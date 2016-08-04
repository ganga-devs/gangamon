from django.conf.urls import patterns, url, include
#.defaults import *

urlpatterns = patterns('monitoringsite.gangausage.views',
    (r'^current', 'current'),
    (r'^day-view', 'dayView'),
    (r'^week-view', 'weekView'),        
    (r'^month-view', 'monthView'),                  
)
