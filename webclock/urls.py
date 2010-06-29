from django.conf.urls.defaults import *

from . import views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^stats/png_graph/(?P<session>\d+)/', views.png_graph),
    (r'^stats/png_graph/', views.png_graph),
    (r'^stats/(\d+)/', views.stats_detail),
    (r'^stats/', views.stats),
)
