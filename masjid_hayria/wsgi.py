"""
WSGI config for masjid_hayria project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from dotenv import load_dotenv
from django.core.wsgi import get_wsgi_application

# `.env` joylashuvi: loyiha ildizida (BASE_DIR/.env). Gunicorn'ni shu yo'ldan
# ishga tushirsa, dotenv avtomatik topadi.
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'masjid_hayria.settings')

application = get_wsgi_application()
