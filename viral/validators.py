from django.core.validators import URLValidator


class NoSchemeURLValidator(URLValidator):
    def __call__(self, value):
        if '://' not in value:
            value = 'http://' + value
        super(NoSchemeURLValidator, self).__call__(value)
