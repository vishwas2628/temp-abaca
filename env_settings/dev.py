from .base import *

CORS_ALLOWED_ORIGINS = [
    "http://localhost:9000"
]

CORS_ORIGIN_REGEX_WHITELIST = (
        r'^(http?://)?localhost:9000',
    r'^(https?://)?dev\.abaca\.app$',
    r'^(https?://)?testing\.abaca\.app$',
    r'^(https?://)?dev-abaca-webapp-stage\.us.aldryn.io$',
    
    # temp changes for local development
    r'^(https?://)?192\.168\.\d{1,3}\.\d{1,3}:\d{1,5}$',

    # This exception was applied to allow local front-end development without using Docker.
    # Please have in mind that this exception shouldn't be replicated to other environments.
    #
    # The data available on this environment is prone to be resetted, as it is a dependency
    # validation environment which runs reset savepoints using Cypress. In this in mind,
    # please use this configuration with caution.
    #
    r'^(https?://)?((\w|-)+\.)?abaca\.pixel:\d{4}$',
)
