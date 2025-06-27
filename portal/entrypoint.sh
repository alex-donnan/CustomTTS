#!/bin/bash

echo "Applying database migrations"
python manage.py migrate
python manage.py makemigrations

echo "Collecting static pages"
python manage.py collectstatic --noinput

exec "$@"