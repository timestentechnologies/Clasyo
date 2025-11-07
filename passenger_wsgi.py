import os
import sys

# Add your project directory to the sys.path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'school_saas.settings'

# Import Django application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
