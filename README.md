# Liine Take Home

## Getting started

### Run via Docker
* `docker compose build`
* `docker compose up`

### Run without Docker
* `python manage.py makemigrations`
* `python manage.py migrate`
* `python manage.py import_restaurants`
* `python manage.py runserver`

## Considerations:
* Due to limited project scope, we are using Django's built-in SQLite database as opposed to more heavy-handed options
* We are using Django's built in lightweight development server, which is NOT suitable for production
  * I wrote a Medium article about better options for this this in 2021: https://medium.com/harvested-financial-engineering/deploying-a-containerized-django-gunicorn-server-on-google-cloud-run-feb13823f7f4