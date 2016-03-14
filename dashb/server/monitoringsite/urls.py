from django.conf.urls.defaults import *
import settings

#from settings import SUB_DIRECTORY

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT,'path':'index.html'}),
    url(r'^django_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url(r'^gangamon/', include('monitoringsite.gangamon.urls')),   
    url(r'^usage/', include('monitoringsite.gangausage.urls')), 
    url(r'^errorreports/', include('monitoringsite.gangaerrorreport.urls')),
    url(r'^cmserrorreports/', include('monitoringsite.cmserrorreport.urls')),                    
    url(r'^usage', 'monitoringsite.gangausage.views.current'),
    url(r'^errorreports', 'monitoringsite.gangaerrorreport.views.default'),
    url(r'^cmserrorreports', 'monitoringsite.cmserrorreport.views.default'),                               

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #(r'^admin/', include(admin.site.urls))
)
