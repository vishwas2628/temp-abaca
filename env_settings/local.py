from .base import *

# Aldryn Django
IS_RUNNING_DEVSERVER = True

# Disable Bugsnag locally
BUGSNAG = {}

CORS_ORIGIN_REGEX_WHITELIST = (
    r'^(https?://)?((\w|-)+\.)?abaca\.app$',
    r'^(https?://)?((\w|-)+\.)?abaca\.pixel:\d{4}$',
    r'^(https?://)?((\w|-)+\.)?abaca\.localhost$',
    r'^(https?://)?localhost:\d{4}$',
    r'^(https?://abaca)?((\w|-)+\.)?us.aldryn.io$',
    r'^(https?://)?((\w|-)+\.)?app\.jetadmin\.io$',
    r'^(https?://)?vildata\.vilcap\.com$',
    # Vendors
    r'^https://(www\.)?(entrep\.net)$',
    r'^https://(www\.)?(entrep\-dev\.com)$',
)

SILKY_MAX_REQUEST_BODY_SIZE = -1  # Silk takes anything <0 as no limit
SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # If response body>1024 bytes, ignore
