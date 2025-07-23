web: python startup.py && daphne -b 0.0.0.0 -p $PORT convolive.asgi:application
worker: python manage.py runworker --settings=convolive.settings
