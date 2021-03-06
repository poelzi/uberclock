from django.conf.urls.defaults import *
from piston.resource import Resource
from uberclock.api import handlers
from piston.doc import documentation_view

user_list_handler = Resource(handlers.UserListHandler)

actions_list_handler = Resource(handlers.ActionsHandler)

detector_handler = Resource(handlers.DetectorHandler)

userprogram_handler = Resource(handlers.UserProgramHandler)


session_handler = Resource(handlers.SessionHandler)
session_entries_handler = Resource(handlers.SessionEntriesHandler)
session_learn_handler = Resource(handlers.SessionLearnHandler)



urlpatterns = patterns('',
   url(r'^docs/', documentation_view),
   url(r'^user/', user_list_handler, name="user_list_handler"),
   url(r'^detector/(?P<id>[^/]+)/', detector_handler, name="detectors_handler"),
   url(r'^detector/$', detector_handler, name="detector_list_handler"),
   url(r'^actions/', actions_list_handler, name="actions_list_handler"),
   url(r'^userprogram/(?P<id>[^/]+)/', userprogram_handler, name="userprogram_handler"),
   url(r'^userprogram/', userprogram_handler, name="userprogram_list_handler"),
   url(r'^session/(?P<session>[^/]+)/learndata/', session_learn_handler, name="session_learn_handler"),
   url(r'^session/(?P<session>[^/]+)/entries/', session_entries_handler, name="session_entries_handler"),
   url(r'^session/(?P<id>[^/]+)/$', session_handler, name="session_handler"),
   url(r'^session/$', session_handler, name="session_list_handler"),
)