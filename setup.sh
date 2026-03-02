#!/bin/bash

# Run migrations
python manage.py migrate

# Compile translations
python manage.py compilemessages -l en -l es

# Prefill default translations fields (if empty)
python manage.py update_translation_fields