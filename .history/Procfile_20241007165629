release: python manage.py migrate
web: gunicorn Shop.wsgi:application --workers 3 --threads 2 --timeout 60 --log-file -