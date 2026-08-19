"""
Django settings for Eventify project.
Combined and configured for Render (Production) & Localhost (Team Development)
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-!derh9#qen0ojn!dqa#@lg=$%)r_zt**o0!kw1qo92)a)oi8yv')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# السماح للـ Host الخاص بـ Render بالعمل
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'authentication', 
    'events.apps.EventsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',              
    'rest_framework',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Eventify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'authentication.context_processors.dashboard_link',
            ],
        },
    },
]

WSGI_APPLICATION = 'Eventify.wsgi.application'


# Database Configuration:
# Dynamic setup -> Postgres on Render OR MySQL/SQLite on Localhost for your team
if os.environ.get('DATABASE_URL'):
    # إعدادات سيرفر Render (PostgreSQL)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }
else:
    # إعدادات العمل المحلي مع الفريق (MySQL أو SQLite)
    # ملاحظة: إذا أردت استخدام MySQL اكتب بياناتها هنا، أو اتركها SQLite
    import pymysql
    pymysql.install_as_MySQLdb()

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# المسار الذي ستجمع فيه مكتبة WhiteNoise الملفات المجهزة للزبون
STATIC_ROOT = BASE_DIR / 'staticfiles'



# Uploaded event images
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Activate the custom user model containing the 3 required roles
AUTH_USER_MODEL = 'authentication.User'

# Admin-only views redirect unauthenticated users to the app login page.
LOGIN_URL = 'login'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if os.environ.get('DATABASE_URL'):
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

# إضافة توافق خلفي لمكتبة django-cloudinary-storage التي لا تزال تفتش
# عن STATICFILES_STORAGE كمتغير مستقل بدل قراءتها من STORAGES
STATICFILES_STORAGE = STORAGES["staticfiles"]["BACKEND"]

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default='dummy_name'),
    'API_KEY': config('CLOUDINARY_API_KEY', default='123456789'),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default='dummy_secret'),
}


# ==========================================
# Email Configuration (Task 2 - Sprint 2)
# ==========================================

# Using decouple to fetch environment variables securely from .env
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'Eventify <noreply@eventify.com>',
)

EMAIL_TIMEOUT = 10

# Use Gmail SMTP when credentials are set. Otherwise print emails in the terminal.
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Public site URL used in email buttons (set this to the Render URL in production).
SITE_URL = config('SITE_URL', default='https://project-b-eventify.onrender.com/').rstrip('/')

CSRF_TRUSTED_ORIGINS = [origin for origin in [SITE_URL] if origin.startswith('http')]
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_host:
    CSRF_TRUSTED_ORIGINS.append(f'https://{render_host}')

