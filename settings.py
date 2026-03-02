# -*- coding: utf-8 -*-
import aldryn_addons.settings
import os
import chargebee

from bugsnag import django as bugsnag_django
from dotenv import load_dotenv

load_dotenv()

# Set env flags
ENV_LIST = ('local', 'dev', 'qa', 'staging', 'production', 'clone')
DEBUG = os.environ.get('DEBUG', 'False')
STAGE = os.environ.get('STAGE', 'remote')
APP_ENV = os.environ.get('APP_ENV', 'local')

# Set available partner/clone apps
CLONE_APP_ESO = 'eso'
CLONE_APP_SMALL_FOUNDATION = 'smallfoundation'

IS_RUNNING_DEVSERVER = APP_ENV == 'local'
IS_DEBUG_ON = DEBUG == 'True' and IS_RUNNING_DEVSERVER

IS_TEST_ENVIRONMENT = APP_ENV == 'staging'
IS_LIVE_ENVIRONMENT = APP_ENV == 'production' or APP_ENV == 'clone'

SECRET_KEY = os.environ.get('SECRET_KEY', 'n(59bvatjhp-mij0lu3r8!82yw=6_lfb8799ip6-y(c$83e0&b')

# Jet Admin
JET_PROJECT = os.environ.get('JET_PROJECT', '')
JET_TOKEN = os.environ.get('JET_TOKEN', '')

# Chargebee
CHARGEBEE_KEY = os.environ.get('CHARGEBEE_KEY', '')
CHARGEBEE_SITE = os.environ.get('CHARGEBEE_SITE', '')

SILKY_AUTHENTICATION = True
SILKY_AUTHORIZATION = True
SILKY_PYTHON_PROFILER = True

# Get rid of Aldryn Django cache warning on local environment:
if STAGE == 'local':
    CACHE_URL = 'locmem://'

# Installed addons from the Divio management dashboard
INSTALLED_ADDONS = [
    # <INSTALLED_ADDONS>  # Warning: text inside the INSTALLED_ADDONS tags is auto-generated. Manual changes will be overwritten.
    'aldryn-addons',
    'aldryn-django',
    # </INSTALLED_ADDONS>
]

aldryn_addons.settings.load(locals())

# Installed applications
INSTALLED_APPS.extend(
    [
        # Third-party applications
        'corsheaders',
        'rest_framework',
        'rest_framework.authtoken',
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'rest_auth',
        'rest_auth.registration',
        'adminsortable',
        'watson',
        'markdownx',
        'gspread',
        'oauth2client',
        'tinymce',
        'sortedm2m',
        'django_better_admin_arrayfield.apps.DjangoBetterAdminArrayfieldConfig',
        'easy_select2',
        'faker',
        'slugify',
        'django.forms',
        'simple_history',
        # Main application
        'shared',
        'viral',
        'grid',
        'matching',
        'profiles',
        'company_lists',
        'milestone_planner',
        'capital_explorer',
        'sdg',
    ]
)
PROJECT_PATH = os.path.abspath(os.path.dirname(__name__))
BUGSNAG = {
    'api_key': 'd5336de53471f6ddcaed2b789d5475cc',
    'project_root': PROJECT_PATH,
    'release_stage': APP_ENV,
    'notify_release_stages': ENV_LIST,
}


# Load Jet Django
if JET_PROJECT and JET_TOKEN:
    INSTALLED_APPS.append('jet_django')

# Priority Apps
INSTALLED_APPS.insert(
    1,
    'modeltranslation',
)

# Debugging Apps
if IS_DEBUG_ON:
    INSTALLED_APPS.append('debug_toolbar')

    # Local Apps
    if IS_RUNNING_DEVSERVER:
        INSTALLED_APPS.append('silk')
        INSTALLED_APPS.append('django_extensions')


# Priority Middleware
MIDDLEWARE.insert(
    0,
    'bugsnag.django.middleware.BugsnagMiddleware',
)

bugsnag_django.configure()

MIDDLEWARE.insert(
    1,
    'corsheaders.middleware.CorsMiddleware',
)

# Additional middlewares
MIDDLEWARE.extend(
    [
        'middlewares.disablecsrf.DisableCSRF',
        'middlewares.vendor_middleware.VendorMiddleware',
        'django.middleware.locale.LocaleMiddleware',
    ]
)

# Debugging Middleware
if IS_DEBUG_ON:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

    # Local Middleware
    if IS_RUNNING_DEVSERVER:
        MIDDLEWARE.insert(2, 'silk.middleware.SilkyMiddleware')


# Conditionally load Admin Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: IS_DEBUG_ON,
    # Disable by default Toolbar panels to avoid bottlenecks on E2E testing
    'DISABLE_PANELS': [
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ],
}

# Celery Configuration Options
CELERY_BROKER_URL = os.environ.get('DEFAULT_AMQP_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672/')

# Configure Chargebee integration
if CHARGEBEE := CHARGEBEE_KEY and CHARGEBEE_SITE:
    chargebee.configure(CHARGEBEE_KEY, CHARGEBEE_SITE)

# Having issue on divio, bugsnag cant find the api key
# adding it here to see if this resolves the issue.
PROJECT_PATH = os.path.abspath(os.path.dirname(__name__))
BUGSNAG = {
    'api_key': 'd5336de53471f6ddcaed2b789d5475cc',
    'project_root': PROJECT_PATH,
    'release_stage': APP_ENV,
    'notify_release_stages': ENV_LIST,
}

# Load specific env settings
if APP_ENV in ENV_LIST:
    exec('from env_settings.%s import *' % APP_ENV)