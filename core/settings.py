import os
import dj_database_url
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

# Render'da SECRET_KEY'i gizli tutmak için environment variable kullanırız
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-kendi-keyini-buraya-yaz')

# Render'da DEBUG'ı Environment Variables'dan alacağız
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['peerlearn-2puj.onrender.com', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users', 
    'notes', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Statik dosyalar için şart
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notes.context_processors.unread_notifications_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# POSTGRESQL AYARI (RENDER İÇİN)
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        ssl_require=True
    )
}

AUTH_USER_MODEL = 'users.CustomUser'

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# --- STATİK AYARLARI ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'ana_sayfa'
LOGOUT_REDIRECT_URL = 'ana_sayfa'
LOGIN_URL = 'login'