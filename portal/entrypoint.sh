#!/bin/bash

echo "Applying database migrations"
python manage.py migrate
python manage.py collectstatic

exec "$@"