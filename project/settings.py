# project/settings.py
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если есть)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------
# Основные настройки
# ---------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key")
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

# ALLOWED_HOSTS — если в .env пустая строка, получим ['']
_allowed = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]

# ---------------------------------------------------------------------
# Приложения
# ---------------------------------------------------------------------

INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'corsheaders',

    # Local apps
    'jobs',
    'candidates',
    'employers',
    'analytics',
]

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------------------------------------------------------------
# ASGI / WSGI
# ---------------------------------------------------------------------

WSGI_APPLICATION = 'project.wsgi.application'
ASGI_APPLICATION = 'project.asgi.application'

# ---------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------

USE_POSTGRES = os.getenv("USE_POSTGRES", "False").lower() in ("1", "true", "yes")

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'smartbot'),
            'USER': os.getenv('POSTGRES_USER', 'smartbot'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'smartbot'),
            'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('CONN_MAX_AGE', 600)),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------
# Redis / Channels
# ---------------------------------------------------------------------

# channels_redis accepts list of hosts: either ("127.0.0.1", 6379) or URL string.
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # Using direct URL works with channels_redis >= 3.0
            "hosts": [REDIS_URL],
        },
    },
}

# ---------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

# ---------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------
# NOTE: не храните секреты в VCS. .env должен быть в .gitignore.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    # SIMPLE_JWT_SECRET_KEY можно задать в .env; в противном случае используется SECRET_KEY
    "SIGNING_KEY": os.getenv("SIMPLE_JWT_SECRET_KEY", SECRET_KEY),
    # опционально: алгоритм
    "ALGORITHM": os.getenv("SIMPLE_JWT_ALGORITHM", "HS256"),
}

# ---------------------------------------------------------------------
# CORS (для фронта)
# ---------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = True  # для разработки; в проде — отключить и настроить конкретные домены

# ---------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------
# Логирование (минимальное)
# ---------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
}

# ---------------------------------------------------------------------
# Прочее
# ---------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
