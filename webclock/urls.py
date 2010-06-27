from django.conf.urls.defaults import *

from . import views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^simple/', views.simple),
)
