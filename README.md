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

Server should be running at `http://locahost:8000`

### Interacting with Server

To return all restaurants open at a given date and time, you can send a request like this:
`http://localhost:8000/restaurants/api/open?datetime=2024-08-27T12:50:00`

## Considerations:
* Due to limited project scope, we are using Django's built-in SQLite database as opposed to more heavy-handed options
* The smaller (40 row) dataset means we are simply returning all restaurants that meet the filtering criteria. If the dataset was reasonably larger, we would want to page this API by accepting offset/limit parameters to improve performance
* We are using Django's built-in lightweight development server, which is NOT suitable for production
  * I wrote a Medium article about better options for this in 2021: https://medium.com/harvested-financial-engineering/deploying-a-containerized-django-gunicorn-server-on-google-cloud-run-feb13823f7f4