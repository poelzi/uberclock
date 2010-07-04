from piston.handler import BaseHandler
from uberclock.db.models import Session, Entry, LearnData
from piston.doc import generate_doc

class SessionListHandler(BaseHandler):
    allowed_methods = ('GET',)
    model = Session

#     @staticmethod
#     def resource_uri():
#         return ('session_list_handler', [])


class SessionHandler(BaseHandler):
    allowed_methods = ('GET',)
    model = Session

#     @staticmethod
#     def resource_uri():
#         return ('session_handler', ['id'])

class SessionEntriesHandler(BaseHandler):
    allowed_methods = ('GET',)
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
