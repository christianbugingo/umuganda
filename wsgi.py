"""
WSGI config for Umuganda project.
This exposes the WSGI callable for deployment platforms.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umuganda.settings')

application = get_wsgi_application()
# Most platforms look for 'app' or 'application'
app = application