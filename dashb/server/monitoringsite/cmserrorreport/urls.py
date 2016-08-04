from django.conf.urls import patterns, url, include
#.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('monitoringsite.cmserrorreport.views',
    (r'^reports', 'default'),   
    (r'^download/(\d+)', 'download'),   
    (r'^login/(\d+)', 'login'),
    (r'^get_reports_JSON', 'get_reports_JSON'), 
)
