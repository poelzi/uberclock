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
    allowed_methods = ('GET','POST', 'PUT', 'DELETE')
    exclude = ('session',)
    model = LearnData

#     @staticmethod
#     def resource_uri():
#         return ('session_learn_handler', ['session'])
