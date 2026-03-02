from .base import *

CORS_ORIGIN_REGEX_WHITELIST = (
    r'^(https?://)?my-staging\.abaca\.app$',
    r'^(https?://)?launch\.abaca\.app$',
    r'^(https?://)?abaca-webapp-stage\.us\.aldryn\.io$',
    r'^(https?://)?abacawebapp-vctesting-55d5f87\.us\.aldryn\.io$',
    r'^(https?://)?((\w|-)+\.)?app\.jetadmin\.io$',
    r'^(https?://)?vildata\.vilcap\.com$',
    # Vendors
    r'^https://(www\.)?(entrep\-dev\.com)$',
)
