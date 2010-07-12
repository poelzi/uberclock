from django.conf.urls.defaults import *

from . import views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^stats/png_graph/(?P<session>\d+)/', views.png_graph),
    (r'^stats/png_graph/', views.png_graph),
    url(r'^stats/merge/(?P<session>\d+)/(?P<source>\d+)/', views.stats_merge, name="stats_merge"),
    url(r'^stats/delete/(?P<session>\d+)/', views.stats_delete, name="stats_delete"),
    url(r'^stats/(\d+)/', views.stats_detail, name="stats"),
    (r'^stats/', views.stats),
)
