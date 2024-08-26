import csv
import os
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils.dateparse import parse_datetime
from io import StringIO
from restaurants.models import Restaurant
from restaurants.views import RestaurantListAPIView
from django.conf import settings


class RestaurantTest(TestCase):

    def setUp(self):
        # Load data from the CSV into the Restaurant model
        self.view = RestaurantListAPIView()
        self.load_csv_data()

    def load_csv_data(self):
        csv_file_path = os.path.join(settings.BASE_DIR, 'restaurants', 'restaurants.csv')
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row['Restaurant Name'].strip()
                hours = row['Hours'].strip()
                Restaurant.objects.create(name=name, hours=hours)

    # Import command Tests
    def test_import_restaurants_success(self):
        Restaurant.objects.create(name="Old Restaurant", hours="Mon-Fri 9 am - 5 pm")
        out = StringIO()
        call_command('import_restaurants', stdout=out)
        self.assertIn('Successfully imported restaurant data', out.getvalue())
        self.assertEqual(Restaurant.objects.count(), 40)
        self.assertTrue(Restaurant.objects.filter(name="The Cowfish Sushi Burger Bar").exists())

    def test_import_restaurants_file_not_found(self):
        with self.assertRaises(CommandError):
            call_command('import_restaurants', 'non_existent_file.csv')

    def test_import_restaurants_invalid_csv(self):
        invalid_csv_content = """
        Wrong Name,Wrong Hours
        Something,Some value
        """
        invalid_file_path = os.path.join(os.path.dirname(__file__), 'invalid_test_restaurants.csv')
        with open(invalid_file_path, 'w') as f:
            f.write(invalid_csv_content)

        with self.assertRaises(CommandError) as cm:
            call_command('import_restaurants', invalid_file_path)

        self.assertIn("CSV file must contain 'Restaurant Name' and 'Hours' columns", str(cm.exception))

        if os.path.exists(invalid_file_path):
            os.remove(invalid_file_path)

    # View Tests
    def test_maximum_open_restaurant_count(self):
        """Test the maximum number of restaurants open given the hours data (Wednesday at 5pm)."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-28T17:00:00'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        open_restaurants = data.get('open_restaurants', [])
        self.assertEqual(len(open_restaurants), 39)

    def test_sunday_open_restaurant_count(self):
        """Test the count of open restaurants on Sunday at 5pm."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-25T17:00:00'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        open_restaurants = data.get('open_restaurants', [])
        self.assertEqual(len(open_restaurants), 36)

    def test_missing_datetime(self):
        """Test that the request returns an error when no datetime parameter is provided."""
        response = self.client.get('/restaurants/api/open')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        err = data.get('error', "")
        self.assertEqual(err, "A 'datetime' query parameter is required.")

    def test_invalid_month(self):
        """Test that the request returns an error when the month is invalid."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-44-25T17:00:00'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        err = data.get('error', "")
        self.assertEqual(err, "month must be in 1..12")

    def test_invalid_day(self):
        """Test that the request returns an error when the day is invalid."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-75T17:00:00'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        err = data.get('error', "")
        self.assertEqual(err, "day is out of range for month")

    def test_invalid_datetime_format(self):
        """Test that the request returns an error when datetime does not contain parseable time information."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-28T3434'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        err = data.get('error', "")
        self.assertEqual(err, "Invalid datetime format. Please use value that specifies a date and a time.")

    def test_valid_date_no_time(self):
        """Test that the request returns an error when datetime is valid but does not contain time information."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-28'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        err = data.get('error', "")
        self.assertEqual(err, "The provided datetime is missing time information. Please include both date and time.")

    def test_open_restaurant(self):
        """Test if a restaurant with specific hours is open on Wednesday at 12:00 PM."""
        restaurant = Restaurant.objects.get(name="The Cowfish Sushi Burger Bar")
        datetime_str = '2024-08-28T12:00:00'  # Wednesday at noon
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertTrue(is_open)

    def test_closed_restaurant(self):
        """Test if a restaurant with specific hours is closed on Wednesday at 5:00 PM."""
        restaurant = Restaurant.objects.get(name="Beasley's Chicken + Honey")
        datetime_str = '2024-08-28T17:00:00'  # Wednesday at 5:00 pm
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertFalse(is_open)

    def test_hours_past_midnight(self):
        """Test if a restaurant is open given hours that extend past midnight."""
        restaurant = Restaurant.objects.get(name="Seoul 116")
        datetime_str = '2024-08-30T03:00:00'  # Friday at 3:00 am
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertTrue(is_open)

    def test_sporadic_hours(self):
        """Test if a restaurant with hours not included in the CSV can be parsed correctly."""
        odd = Restaurant.objects.create(
            name="Odd Cafe",
            hours="Mon 3:30 pm - 2 am / Wed 4 pm - 5 pm / Fri 12 am - 12 am"
        )
        datetime_str_next_day = '2024-09-03T01:00:00'  # Tuesday at 1 am
        datetime_str_all_day = '2024-08-30T00:07:00'  # Friday at 12:07 am
        datetime_obj_next_day = parse_datetime(datetime_str_next_day)
        datetime_obj_all_day = parse_datetime(datetime_str_all_day)
        parsed_hours = self.view.parse_hours(odd.hours)
        is_open_next_day = self.view.check_open_hours(parsed_hours, datetime_obj_next_day)
        is_open_all_day = self.view.check_open_hours(parsed_hours, datetime_obj_all_day)
        self.assertTrue(is_open_next_day)
        self.assertTrue(is_open_all_day)

    def test_24_hour_operation(self):
        """Test a restaurant that operates 24 hours a day."""
        all_day = Restaurant.objects.create(
            name="24/7 Diner",
            hours="Mon-Sun 12:00 am - 12:00 am"
        )
        datetime_str = '2024-08-27T15:00:00'  # Any time of the day
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(all_day.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertTrue(is_open)

    def test_non_contiguous_days(self):
        """Test a restaurant with non-contiguous operating days."""
        restaurant = Restaurant.objects.create(
            name="Selective Eats",
            hours="Mon-Wed 8:00 am - 5:00 pm / Fri 10:00 am - 8:00 pm"
        )
        datetime_str = '2024-08-30T11:00:00'  # Friday at 11:00 am
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertTrue(is_open)
