import os,os.path
import sys

#Change this directory prefix if the application is installed to another location
PREFIX='/data/gangamon'

sys.path.append(os.path.join(PREFIX,'dashboard/server'))
# needed only when pyggoglechart is not installed in the system
sys.path.append(os.path.join(PREFIX,'external/pygooglechart')) 

os.environ['DJANGO_SETTINGS_MODULE'] = 'monitoringsite.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
