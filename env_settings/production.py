from .base import *

CORS_ORIGIN_REGEX_WHITELIST = (
    r'^https://api\.abaca\.app$',
    r'^(https?://)?my\.abaca\.app$',
    r'^(https?://)?abaca-webapp\.us\.aldryn\.io$',
    r'^(https?://)?((\w|-)+\.)?app\.jetadmin\.io$',
    r'^(https?://)?vildata\.vilcap\.com$',
    # Vendors
    r'^https://(www\.)?(entrep\.net)$',
)

WEBHOOKS['REQUEST_EXTERNAL_COMPANY_DATA'] = 'https://hook.integromat.com/s2av1ed4pewl34gvf8miap5fph72clc5'
