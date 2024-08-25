import csv
import os
from django.test import TestCase
from django.utils.dateparse import parse_datetime

from liine import settings
from .models import Restaurant
from .views import RestaurantListAPIView


class RestaurantCSVTest(TestCase):

    def setUp(self):
        # Load data from the CSV into the Restaurant model
        self.view = RestaurantListAPIView()
        self.load_csv_data()

    def load_csv_data(self):
        csv_file_path = os.path.join(settings.BASE_DIR, 'restaurants', 'restaurants.csv')
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name, hours = row
                Restaurant.objects.create(name=name, hours=hours)

    def test_maximum_open_restaurant_count(self):
        """Test the maximum number of restaurants open given the hours data (Wednesday at 5pm)."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-28T17:00:00'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        open_restaurants = data.get('open_restaurants', [])
        # Expect 39/40 restaurants open - Beasley's hours are obnoxious
        self.assertEqual(len(open_restaurants), 39)

    def test_sunday_open_restaurant_count(self):
        """Test the count of open restaurants on Sunday at 5pm."""
        response = self.client.get('/restaurants/api/open', {'datetime': '2024-08-25T17:00:00'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        open_restaurants = data.get('open_restaurants', [])
        # Expect 37/40 restaurants open - two are not open on Sunday and one closes at 3pm
        self.assertEqual(len(open_restaurants), 37)

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
        datetime_str = '2024-08-28T17:00:00'  # Wednesday at 5:00 PM
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertFalse(is_open)

    def test_hours_past_midnight(self):
        """Test if a restaurant is open given hours that extend past midnight."""
        restaurant = Restaurant.objects.get(name="Seoul 116")
        datetime_str = '2024-08-30T03:00:00'  # Friday at 3:00 AM
        datetime_obj = parse_datetime(datetime_str)
        parsed_hours = self.view.parse_hours(restaurant.hours)
        is_open = self.view.check_open_hours(parsed_hours, datetime_obj)
        self.assertTrue(is_open)
