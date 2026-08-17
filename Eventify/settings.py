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
    'cloudinary_storage',       # ضرورية قبل staticfiles
    'django.contrib.staticfiles',
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

# Storage engine for WhiteNoise (Optimized serving)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Uploaded event images
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Activate the custom user model containing the 3 required roles
AUTH_USER_MODEL = 'authentication.User'

# Admin-only views redirect unauthenticated users to the app login page.
LOGIN_URL = 'login'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files configuration
# --- Media & Cloudinary Configuration ---
MEDIA_URL = '/media/'

# إذا كنت تريد تخزين كل شيء على Cloudinary دائماً (سواء محلي أو سيرفر):
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# إعدادات Cloudinary (تُجلب من ملف .env)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}
