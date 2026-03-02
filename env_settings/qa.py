from .base import *

CORS_ORIGIN_REGEX_WHITELIST = (
    r'^(https?://)?qa\.abaca\.app$',
    r'^(https?://)?dev-abaca-webapp\.us.aldryn.io$',
    r'^(https?://)?abacawebapp-qa-ab1d200\.us.aldryn.io$',
    # TODO: remove this line when vue3 migration is complete
    r'^(https?://)?vue3\.abaca\.app$',
)