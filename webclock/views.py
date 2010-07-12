# Create your views here.
# Create your views here.
import datetime, os, re

from django.utils.translation import gettext as _
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse


from django.utils.translation import gettext as _

from uberclock.db.models import Entry, Session
from uberclock.webclock.decorators import confirm_required

INDEX_PATH = os.path.join(os.path.dirname(__file__), 
                           "templates", "webclock", "index")

def get_clock_types():
    res = {}
    for item in os.listdir(INDEX_PATH):
        # read the content
        try:
            content = open(os.path.join(INDEX_PATH, item)).read()
        except IOError:
            continue
        match = re.search("webclock_name (.*)", content)
        if match:
            res[os.path.basename(item)] = match.group(1)
    for name in settings.CHUMBY_URLS:
        res["chumby_%s" %name] = "Chumby: %s" %name
    return res


def index(request):
    types = get_clock_types()

    data = {"types": types}


    typ = request.COOKIES.get("webclock_clock", "simple.html")

    typ = request.GET.get("typ", typ)
    
    if typ[:7] == 'chumby_':
        data["chumby_code"] = settings.CHUMBY_URLS.get(typ[7:], "")
        template = "chumby.html"
    else:
        if not typ in types:
            typ = "simple.html"
        template = typ

    data["current"] = typ

    ret = render_to_response('webclock/index/%s' %template,
                              data,
                              context_instance=RequestContext(request))

    if request.COOKIES.get("webclock_clock", "simple.html") != typ:
        ret.set_cookie("webclock_clock", value=typ)

    return ret


def stats(request):
    now = datetime.datetime.now()

    typ = request.COOKIES.get("webclock_stats", "png")
    typ = request.GET.get("typ", typ)

    if typ not in ["js", "png"]:
        typ = "png"

    data = {
        'now': now,
        'now_week': now.isocalendar()[1],
        'sessions': Session.objects.all().order_by("-id"),
        'current': typ
        }

    ret = render_to_response('stats.html',
                              data,
                              context_instance=RequestContext(request))

    if request.COOKIES.get("webclock_stats", "png") != typ:
        ret.set_cookie("webclock_stats", value=typ)

    return ret

def stats_detail(request, session):
    now = datetime.datetime.now()
    sess = get_object_or_404(Session, id__exact=session)

    try:
        next = Session.objects.filter(id__gt=sess.id)[0]
    except IndexError:
        next = None

    try:
        prev = Session.objects.filter(id__lt=sess.id).order_by('-id')[0]
    except IndexError:
        prev = None

    typ = request.COOKIES.get("webclock_stats", "png")
    typ = request.GET.get("typ", typ)

    if typ == "js":
        template = 'stats_detail_js.html'

    else:
        template = 'stats_detail.html'
        typ = "png"
        

    data = {
        'prev': prev,
        'next': next,
        'now': now,
        'now_week': now.isocalendar()[1],
        'session': sess,
        'current': typ
        }

    ret = render_to_response(template,
                              data,
                              context_instance=RequestContext(request))
    
    if request.COOKIES.get("webclock_stats", "png") != "png":
        ret.set_cookie("webclock_stats", value=typ)

    return ret


def merge_session_context(request, session, source):
    session = get_object_or_404(Session, id=session)
    source = get_object_or_404(Session, id=source)
    return RequestContext(request, {'session': session, 'source': source})

@confirm_required('webclock/confirm_merge.html', merge_session_context)
def stats_merge(request, session, source):

    sess = get_object_or_404(Session, id__exact=session)
    sess.merge(Session.objects.get(id__exact=source))
    
    messages.add_message(request, messages.INFO, _("Successfull merged"))

    return HttpResponseRedirect(reverse("stats", args=(session,)))

def stats_delete(request, session):
    pass



# file charts.py
def png_graph(request, session=None):
    import random
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from matplotlib.figure import Figure
        from matplotlib.dates import DateFormatter
    except:
        return HttpResponse("Install matplotlib to see graphics", status=500)

    fig=Figure()
    ax=fig.add_subplot(111)
    x=[]
    y=[]

    if Session.objects.all().count():
        if session:
            sess = get_object_or_404(Session, id__exact=session)
        else:
            sess = Session.objects.all().order_by("-id")[0]

#     now=datetime.datetime.now()
#     delta=datetime.timedelta(days=1)
#     for i in range(10):
#         x.append(now)
#         now+=delta
#         y.append(random.randint(0, 1000))
        for entry in sess.entry_set.all():
            x.append(entry.date)
            y.append(entry.value)
    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%H:%m'))
    fig.autofmt_xdate()
    canvas=FigureCanvas(fig)
    response=HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
