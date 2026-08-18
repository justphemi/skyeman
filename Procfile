web: gunicorn skyeman_project.wsgi --log-file -
release: python manage.py migrate && python manage.py seed
