import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from restaurants.models import Restaurant
from django.conf import settings

class Command(BaseCommand):
    help = 'Import restaurants data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file_path',
            nargs='?',
            default=os.path.join(settings.BASE_DIR, 'restaurants', 'restaurants.csv'),
            help='The path to the CSV file containing restaurant data'
        )

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file_path']

        if not os.path.exists(csv_file_path):
            raise CommandError(f"CSV file not found: {csv_file_path}")

        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                if 'Restaurant Name' not in reader.fieldnames or 'Hours' not in reader.fieldnames:
                    raise CommandError("CSV file must contain 'Restaurant Name' and 'Hours' columns")

                with transaction.atomic():
                    # Delete existing restaurant data
                    Restaurant.objects.all().delete()
                    self.stdout.write(self.style.WARNING('Existing restaurant data deleted'))

                    # Import new restaurant data
                    for row in reader:
                        name = row['Restaurant Name'].strip()
                        hours = row['Hours'].strip()

                        if not name or not hours:
                            self.stdout.write(self.style.WARNING(f"Skipping incomplete row: {row}"))
                            continue

                        Restaurant.objects.create(name=name, hours=hours)

            self.stdout.write(self.style.SUCCESS('Successfully imported restaurant data'))

        except Exception as e:
            raise CommandError(f"An error occurred: {e}")
