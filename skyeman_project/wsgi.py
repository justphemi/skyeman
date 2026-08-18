"""WSGI config for the Skyeman project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skyeman_project.settings")
application = get_wsgi_application()
