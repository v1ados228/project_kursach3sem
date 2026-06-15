#!/bin/sh
set -e

python manage.py migrate
python manage.py setup_roles
python manage.py collectstatic --noinput 2>/dev/null || true
python manage.py runserver 0.0.0.0:8000
