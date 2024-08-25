import csv
import os
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant
from django.conf import settings

class Command(BaseCommand):
    help = 'Import restaurants data from CSV file'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(settings.BASE_DIR, 'restaurants', 'restaurants.csv')
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row['name']
                hours = row['hours']

                # Create or update the Restaurant record
                restaurant, created = Restaurant.objects.get_or_create(name=name, defaults={'hours': hours})
                if not created:
                    restaurant.hours = hours
                    restaurant.save()

        self.stdout.write(self.style.SUCCESS('Successfully imported restaurant data'))
