from django.conf.urls.defaults import *
from piston.resource import Resource
from uberclock.api.handlers import SessionHandler, SessionListHandler, SessionEntriesHandler, SessionLearnHandler
from piston.doc import documentation_view


session_handler = Resource(SessionHandler)
session_list_handler = Resource(SessionListHandler)
session_entries_handler = Resource(SessionEntriesHandler)
session_learn_handler = Resource(SessionLearnHandler)


urlpatterns = patterns('',
   #url(r'^docs/', show_docs),
   url(r'^docs/', documentation_view),
   url(r'^session/(?P<session>[^/]+)/learndata/', session_learn_handler, name="session_learn_handler"),
   url(r'^session/(?P<session>[^/]+)/entries/', session_entries_handler, name="session_entries_handler"),
   url(r'^session/(?P<id>[^/]+)/', session_handler, name="session_handler"),
   url(r'^session/', session_list_handler, name="session_list_handler"),
)