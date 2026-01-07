from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = [host.strip() for host in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')]

# CSRF trusted origins for both development and production
# First add all HTTPS origins from ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = [f'https://{host.strip()}' for host in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')]

# Add HTTP versions for all hosts (needed for development and some production scenarios)
CSRF_TRUSTED_ORIGINS += [f'http://{host.strip()}' for host in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')]

# Add development preview server origins
CSRF_TRUSTED_ORIGINS += ['http://127.0.0.1:8000', 'http://localhost:8000']

# Add any additional custom domains from environment variable
ADDITIONAL_TRUSTED_ORIGINS = config('ADDITIONAL_TRUSTED_ORIGINS', default='').split(',')
if ADDITIONAL_TRUSTED_ORIGINS and ADDITIONAL_TRUSTED_ORIGINS[0]:
    for origin in ADDITIONAL_TRUSTED_ORIGINS:
        if origin.strip():
            CSRF_TRUSTED_ORIGINS += [f'https://{origin.strip()}', f'http://{origin.strip()}']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    
    # Third party apps
    'guardian',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'ckeditor',
    
    # Project apps
    'tenants',
    'subscriptions',
    'superadmin',
    'core',
    'accounts',
    'students',
    'academics',
    'fees',
    'examinations',
    'online_exam',
    'homework',
    'human_resource',
    'leave_management',
    'communication',
    'library',
    'inventory',
    'transport',
    'dormitory',
    'reports',
    'frontend',
    'certificates',
    'attendance',
    'lesson_plan',
    'chat',
    'clubs',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'tenants.middleware.TenantMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.maintenance_middleware.MaintenanceModeMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.ImpersonationMiddleware',  # Login As functionality
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_saas.urls'

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
                'django.template.context_processors.media',
                'core.context_processors.school_context',  # Add school to all templates
                'superadmin.context_processors.impersonation_context',  # Add impersonation status
            ],
        },
    },
]

WSGI_APPLICATION = 'school_saas.wsgi.application'
ASGI_APPLICATION = 'school_saas.asgi.application'

# Database
DB_ENGINE = config('DB_ENGINE', default='sqlite3')

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='school_saas'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
                'use_unicode': True,
            },
        }
    }
else:
    # Default to SQLite for development
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

# Authentication
AUTH_USER_MODEL = 'accounts.User'
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = 'accounts:login'
# LOGIN_REDIRECT_URL for social logins (regular email/password handled in LoginView)
LOGIN_REDIRECT_URL = '/accounts/social-login-complete/'
LOGOUT_REDIRECT_URL = 'frontend:home'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(config('REDIS_HOST', default='127.0.0.1'), config('REDIS_PORT', default=6379, cast=int))],
        },
    },
}

# Payment Gateway Configuration
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

# SMS Configuration
SMS_API_KEY = config('SMS_API_KEY', default='')
SMS_SENDER_ID = config('SMS_SENDER_ID', default='SCHOOL')

# CKEditor Configuration
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
        'extraPlugins': 'colorbutton,colordialog,font,justify,showblocks',
        'removePlugins': 'save,newpage,preview,print,templates',
        'allowedContent': True,
        'forcePasteAsPlainText': False,
        'basicEntities': False,
        'entities': False,
        'entities_greek': False,
        'entities_latin': False,
        'htmlEncodeOutput': False,
        'fillEmptyBlocks': False,
        'tabSpaces': 4,
        'versionCheck': False,
        'scayt_autoStartup': False,
        'disableNativeSpellChecker': False,
        'browserContextMenuOnCtrl': True,
    },
}

# Disable CKEditor version check to prevent security warnings
CKEDITOR_ALLOW_NONIMAGE_FILES = True
CKEDITOR_BROWSE_SHOW_DIRS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    # Development servers
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:62469",
    "http://localhost:62469",
]

# Add allowed hosts to CORS origins
for host in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(','):
    if host.strip() and host.strip() not in ['localhost', '127.0.0.1']:
        CORS_ALLOWED_ORIGINS.extend([f'https://{host.strip()}', f'http://{host.strip()}'])

# Add additional CORS origins from environment variable
ADDITIONAL_CORS_ORIGINS = config('ADDITIONAL_CORS_ORIGINS', default='').split(',')
if ADDITIONAL_CORS_ORIGINS and ADDITIONAL_CORS_ORIGINS[0]:
    for origin in ADDITIONAL_CORS_ORIGINS:
        if origin.strip():
            CORS_ALLOWED_ORIGINS.extend([f'https://{origin.strip()}', f'http://{origin.strip()}'])


# Tenant settings
TENANT_SUBFOLDER_PREFIX = 'school'

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# Session Settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Security Settings (Enable in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# PDF Generation Settings
PDFKIT_CONFIG = {
    'wkhtmltopdf': r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
    'encoding': 'UTF-8',
    'quiet': ''
}
