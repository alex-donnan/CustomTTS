#!/bin/sh

echo "Applying database migrations"
python manage.py makemigrations
python manage.py migrate

echo "Collecting static pages"
python manage.py collectstatic --noinput

echo "Starting Django"
gunicorn portal.wsgi:application --bind 0.0.0.0:1500

exec "$@"