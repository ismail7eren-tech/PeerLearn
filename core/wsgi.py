import os
from django.core.wsgi import get_wsgi_application

# Django'nun hangi ayar dosyasını kullanacağını sisteme tanıtıyoruz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()