#!/bin/bash

# Ensure the mock database only gets initialized on the proper environment:
if [[ -z "$APP_ENV" ]] || [[ ! $APP_ENV =~ ^local|dev$ ]]; then
  echo "Skipping mock-database initialization."
  exit
fi

# Setup Mock Database
python manage.py database_savepoint -a setup

# Store Mock Savepoint
python manage.py database_savepoint -a store
