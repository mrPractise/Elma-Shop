web: gunicorn Shop.wsgi --log-file elma_shop_error.log  
web: python manage.py migrate && gunicorn Shop.wsgi