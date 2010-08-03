from piston.handler import BaseHandler
from piston.doc import generate_doc
from piston.utils import rc, require_mime, require_extended, FormValidationError

from uberclock.db.models import Detector, Session, Entry, LearnData
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse

import re
#
#     start = models.DateTimeField("Start", null=False, auto_now_add=True, editable=False)
#     stop = models.DateTimeField("Stop", null=False, auto_now_add=True, editable=False)
#     user = models.ForeignKey(User, null=True)
#     detector = models.ForeignKey(Detector, null=True, blank=True)
#     program = models.ForeignKey(UserProgram, null=True, blank=True)
#     wakeup = models.DateTimeField("Wakeup", null=True, blank=True)
#     #FIXME messure real slept length
#     sleep_time = models.IntegerField(null=True, help_text="Minutes of wanted sleep", blank=True)
#     window = models.IntegerField(null=True, blank=True, help_text="Window of Minutes how many minutes before wakeup can be alarmed")
#     rating = models.IntegerField("Rating", null=True, blank=True)
#     deleted = models.BooleanField("Deleted", default=False)
#     rf_id = models.IntegerField("RF Id", null=True)
#     closed = models.BooleanField("Session has ended", default=False)
#     new = models.BooleanField("Session has not yet run", default=False)
#
#     lights_action = models.CharField("Lights Action", max_length=30, default="lights", choices=ACTION_CHOICES)
#     wakeup_action = models.CharField("Wakeup Action", max_length=30, default="wakeup", choices=ACTION_CHOICES)
#

class UserListHandler(BaseHandler):
    allowed_methods = ('GET',)
    model = User
    exclude = ("password",)
#     fields = ('id', 
#               'username', 
#               'start', 'stop', 
#               ('detector', ('id', 'name')),
#               ('program', ('id',)),
#               'closed', 'new')


class DetectorHandler(BaseHandler):
    allowed_methods = ('GET',)
    model = Detector
    fields = ('id', 
              'name', 
              'typ',
              'typ_display',
              'ident',
              ('default_user', ('id', 'username')))

class DetectorListHandler(DetectorHandler):
    allowed_methods = ('GET',)


# SESSIONS
class SessionListHandler(BaseHandler):
    allowed_methods = ('GET', 'PUT', 'POST')
    model = Session
    fields = ('id', 
              ('user', ('id', 'username')), 
              'start', 'stop', 
              ('detector', ('id', 'name')),
              ('program', ('id',)),
              'closed', 'new')

   #fields = (re.compile('.*'),)



    #include = ('id',)


#     @staticmethod
#     def resource_uri():
#         return ('session_list_handler', [])


class SessionHandler(BaseHandler):
    allowed_methods = ('GET', 'POST')
    model = Session

    fields = ("id",
              "start",
              "stop",
              ("user", ("id", "username")),
              ("detector", ("id", "name")),
              ("program", ("id",)),
              "wakeup",
              "sleep_time",
              "window",
              "rating",
              "rf_id",
              "closed",
              "new",
              "lights_action",
              "wakeup_action")

    def create(self, request):
        """
        Creates a new blogpost.
        """
        attrs = self.flatten_dict(request.POST)
        args = self.flatten_dict(request.POST)

        if "id" in attrs:
            return rc.DUPLICATE_ENTRY
        else:
            # set default user to current user
            if request.user and not request.user.is_anonymous():
                args["user"] = request.user
            
            if "user" in attrs:
                try:
                    usr = User.objects.get(id=int(attrs["user"]))
                except ValueError, Users.DoesNotExist:
                    usr = User.objects.get(username=attrs["user"])
                args["user"] = usr
            if "detector" in attrs:
                args["detector"] = Detector.get(id=attrs["detector"])

            post = Session(**args)
            post.clean_fields()

            try:
                post.save()
            except Exception:
                import traceback
                traceback.print_exc()
            return post


class ActionsHandler(BaseHandler):
    allowed_methods = ('GET',)

    def read(self, request):
        rv = []
        for key, var in settings.COMMANDS.iteritems():
            rv.append({"id":key, "type":var.get("type", "execute"), "name":var.get("name", key), "desc":var.get("description", None)})

        return rv


class SessionEntriesHandler(BaseHandler):
    allowed_methods = ('GET', 'PUT', 'POST')
    #exclude = ('session','resource_uri')
    fields = ("date", "counter", "id", "value")
    model = Entry

#    @staticmethod
#    def resource_uri():
#        return ('session_entries_handler', ['session'])

class SessionLearnHandler(BaseHandler):
    allowed_methods = ('GET', 'POST', 'DELETE')
    exclude = ('session',)
    model = LearnData

    def read(self, request, session=None):
        return Session.objects.get(id=session).learndata

    def create(self, request, *args, **kwargs):

        session = Session.objects.get(id=kwargs["session"])
        ld = session.learndata

        for key in ["wake", "lights", "start", "stop"]:
            if key in request.POST:
                if session.entry_set.filter(id=request.POST[key]).count():
                    setattr(ld, "%s_id" %key, request.POST[key])
            else:
                setattr(ld, "%s_id" %key, None)

        ld.save()

        return ld
