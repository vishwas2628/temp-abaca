import os
import settings
from django.utils.translation import gettext_lazy as _

SITE_ID = 1

SAFE_EXTERNAL_FILE_SIZE = 2097152  # 2MB

# Internationalization
USE_I18N = True
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
]

# Aldryn Django
IS_RUNNING_DEVSERVER = False

# Configure Auth
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Already defined Django-related contexts here
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # `allauth` needs this from django
                'django.template.context_processors.request',
                'django.template.context_processors.static',
            ],
        },
    },
]

ACCOUNT_ADAPTER = 'viral.adapter.CustomAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = os.getenv(
    'ACCOUNT_EMAIL_VERIFICATION', 'mandatory')
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",

    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Configure CORS
CORS_ALLOW_CREDENTIALS = True

DEFAULT_RENDERER_CLASSES = (
    'rest_framework.renderers.JSONRenderer',
)

# Set Browsable API availability
if os.getenv('DEBUG', False):
    DEFAULT_RENDERER_CLASSES = DEFAULT_RENDERER_CLASSES + (
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'viral.utils.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'viral.permissions.AdminLoginAsAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': DEFAULT_RENDERER_CLASSES
}

REST_AUTH_SERIALIZERS = {
    'LOGIN_SERIALIZER': 'viral.serializers.CustomLoginSerializer',
}

PROJECT_PATH = os.path.abspath(os.path.dirname(__name__))
BUGSNAG = {
    'api_key': 'd5336de53471f6ddcaed2b789d5475cc',
    'project_root': PROJECT_PATH,
    'release_stage': settings.APP_ENV,
    'notify_release_stages': settings.ENV_LIST,
}

WEBHOOKS = {
    # Get logo, about, etc from external providers
    'REQUEST_EXTERNAL_COMPANY_DATA': ''
}

# Needed to override widget's default templates
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'
