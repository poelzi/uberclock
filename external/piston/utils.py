from django.http import HttpResponseNotAllowed, HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django import get_version as django_version
from decorator import decorator

from datetime import datetime, timedelta

__version__ = '0.2.2'

def get_version():
    return __version__

def format_error(error):
    return u"Piston/%s (Django %s) crash report:\n\n%s" % \
        (get_version(), django_version(), error)

class rc_factory(object):
    """
    Status codes.
    """
    CODES = dict(ALL_OK = ('OK', 200),
                 CREATED = ('Created', 201),
                 DELETED = ('', 204), # 204 says "Don't send a body!"
                 BAD_REQUEST = ('Bad Request', 400),
                 FORBIDDEN = ('Forbidden', 401),
                 NOT_FOUND = ('Not Found', 404),
                 DUPLICATE_ENTRY = ('Conflict/Duplicate', 409),
                 NOT_HERE = ('Gone', 410),
                 NOT_IMPLEMENTED = ('Not Implemented', 501),
                 THROTTLED = ('Throttled', 503))

    def __getattr__(self, attr):
        """
        Returns a fresh `HttpResponse` when getting 
        an "attribute". This is backwards compatible
        with 0.2, which is important.
        """
        try:
            (r, c) = self.CODES.get(attr)
        except TypeError:
            raise AttributeError(attr)

        return HttpResponse(r, content_type='text/plain', status=c)
    
rc = rc_factory()
    
class FormValidationError(Exception):
    def __init__(self, form):
        self.form = form

class HttpStatusCode(Exception):
    def __init__(self, response):
        self.response = response

def validate(v_form, operation='POST'):
    @decorator
    def wrap(f, self, request, *a, **kwa):
        form = v_form(getattr(request, operation))
    
        if form.is_valid():
            return f(self, request, *a, **kwa)
        else:
            raise FormValidationError(form)
    return wrap

def throttle(max_requests, timeout=60*60, extra=''):
    """
    Simple throttling decorator, caches
    the amount of requests made in cache.
    
    If used on a view where users are required to
    log in, the username is used, otherwise the
    IP address of the originating request is used.
    
    Parameters::
     - `max_requests`: The maximum number of requests
     - `timeout`: The timeout for the cache entry (default: 1 hour)
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        if request.user.is_authenticated():
            ident = request.user.username
        else:
            ident = request.META.get('REMOTE_ADDR', None)
    
        if hasattr(request, 'throttle_extra'):
            """
            Since we want to be able to throttle on a per-
            application basis, it's important that we realize
            that `throttle_extra` might be set on the request
            object. If so, append the identifier name with it.
            """
            ident += ':%s' % str(request.throttle_extra)
        
        if ident:
            """
            Preferrably we'd use incr/decr here, since they're
            atomic in memcached, but it's in django-trunk so we
            can't use it yet. If someone sees this after it's in
            stable, you can change it here.
            """
            ident += ':%s' % extra
    
            now = datetime.now()
            ts_key = 'throttle:ts:%s' % ident
            timestamp = cache.get(ts_key)
            offset = now + timedelta(seconds=timeout)
    
            if timestamp and timestamp < offset:
                t = rc.THROTTLED
                wait = timeout - (offset-timestamp).seconds
                t.content = 'Throttled, wait %d seconds.' % wait
                
                return t
                
            count = cache.get(ident, 1)
            cache.set(ident, count+1)
            
            if count >= max_requests:
                cache.set(ts_key, offset, timeout)
                cache.set(ident, 1)
    
        return f(self, request, *args, **kwargs)
    return wrap

def coerce_put_post(request):
    """
    Django doesn't particularly understand REST.
    In case we send data over PUT, Django won't
    actually look at the data and load it. We need
    to twist its arm here.
    
    The try/except abominiation here is due to a bug
    in mod_python. This should fix it.
    """
    if request.method == "PUT":
        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = "PUT"
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = 'PUT'
            
        request.PUT = request.POST


class MimerDataException(Exception):
    """
    Raised if the content_type and data don't match
    """
    pass

class Mimer(object):
    TYPES = dict()
    
    def __init__(self, request):
        self.request = request
        
    def is_multipart(self):
        content_type = self.content_type()
        if content_type is not None:
            return content_type.lstrip().startswith('multipart')
        return False

    def loader_for_type(self, ctype):
        """
        Gets a function ref to deserialize content
        for a certain mimetype.
        """
        for loadee, mimes in Mimer.TYPES.iteritems():
            if ctype in mimes:
                return loadee

    def content_type(self):
        """
        Returns the content type of the request in all cases where it is
        different than a submitted form - application/x-www-form-urlencoded
        """
        type_formencoded = "application/x-www-form-urlencoded"

        ctype = self.request.META.get('CONTENT_TYPE', type_formencoded)

        # normalize content type
        if ctype.find(';') != -1:
            ctype = ctype[:ctype.find(';')]

        if ctype == type_formencoded:
            return None

        return ctype


    def translate(self):
        """
        Will look at the `Content-type` sent by the client, and maybe
        deserialize the contents into the format they sent. This will
        work for JSON, YAML, XML and Pickle. Since the data is not just
        key-value (and maybe just a list), the data will be placed on
        `request.data` instead, and the handler will have to read from
        there.
        
        It will also set `request.content_type` so the handler has an easy
        way to tell what's going on. `request.content_type` will always be
        None for form-encoded and/or multipart form data (what your browser sends.)
        """    
        ctype = self.content_type()
        self.request.content_type = ctype
        
        if not self.is_multipart() and ctype:
            loadee = self.loader_for_type(ctype)
            
            try:
                self.request.data = loadee(self.request.raw_post_data)
                
                # Reset both POST and PUT from request, as its
                # misleading having their presence around.
                self.request.POST = self.request.PUT = dict()
            except (TypeError, ValueError):
                raise MimerDataException

        return self.request
                
    @classmethod
    def register(cls, loadee, types):
        cls.TYPES[loadee] = types
        
    @classmethod
    def unregister(cls, loadee):
        return cls.TYPES.pop(loadee)

def translate_mime(request):
    request = Mimer(request).translate()
    
def require_mime(*mimes):
    """
    Decorator requiring a certain mimetype. There's a nifty
    helper called `require_extended` below which requires everything
    we support except for post-data via form.
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        m = Mimer(request)
        realmimes = set()

        rewrite = { 'json':   'application/json',
                    'yaml':   'application/x-yaml',
                    'xml':    'text/xml',
                    'pickle': 'application/python-pickle' }

        for idx, mime in enumerate(mimes):
            realmimes.add(rewrite.get(mime, mime))

        if not m.content_type() in realmimes:
            return rc.BAD_REQUEST

        return f(self, request, *args, **kwargs)
    return wrap

require_extended = require_mime('json', 'yaml', 'xml', 'pickle')
    
