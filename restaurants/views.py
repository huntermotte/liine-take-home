import re
from datetime import datetime, time
from rest_framework import generics, status
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from .models import Restaurant
from .serializers import RestaurantSerializer


class RestaurantListAPIView(generics.ListAPIView):
    serializer_class = RestaurantSerializer

    def get(self, request, *args, **kwargs):
        """
        Optionally restricts the returned restaurants to those open at a specific datetime,
        by filtering against a `datetime` query parameter in the URL.
        """
        queryset = Restaurant.objects.all()
        datetime_str = self.request.query_params.get('datetime', None)

        if datetime_str is None:
            return Response(
                {"error": "A 'datetime' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            datetime_obj = parse_datetime(datetime_str)
            if datetime_obj is None:
                raise ValueError("Invalid datetime format. Please use value that specifies a date and a time.")
            open_restaurant_names = []

            for restaurant in queryset:
                if self.is_open(restaurant, datetime_obj):
                    open_restaurant_names.append(restaurant.name)

            return Response({"open_restaurants": open_restaurant_names}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def is_open(self, restaurant, datetime_obj):
        # Parse the restaurant's `hours` field
        open_hours = restaurant.hours  # This should be parsed into a more usable format
        parsed_hours = self.parse_hours(open_hours)

        # Check if `datetime_obj` falls within the open hours
        if self.check_open_hours(parsed_hours, datetime_obj):
            return True
        return False

    def parse_time(self, time_str):
        """Convert time string like '11:00 am' or '12:30 pm' or '10 pm' into a datetime.time object."""
        try:
            # Try parsing time with minutes
            return datetime.strptime(time_str.strip(), '%I:%M %p').time()
        except ValueError:
            # If there's no minutes, try parsing without minutes
            return datetime.strptime(time_str.strip(), '%I %p').time()

    def parse_hours(self, hours_str):
        """Parse the hours string into a structured format."""
        day_map = {
            'Mon': 'Monday', 'Tues': 'Tuesday', 'Wed': 'Wednesday', 'Thu': 'Thursday',
            'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'
        }
        hours_dict = {day: [] for day in day_map.values()}

        # Split by '/' to handle different day/time groups
        # 1. A-Za-z: All alphabetic characters.
        # 2. ,: The comma character to separate days.
        # 3. \s: Whitespace (space, tab, etc.).
        # 4. -: The hyphen character at the end of the class, which now correctly represents a literal hyphen.
        parts = hours_str.split('/')

        # Regex to find day ranges and times
        day_time_pattern = re.compile(r'([A-Za-z,\s-]+)\s+([\d:\sampm-]+)')

        for part in parts:
            match = day_time_pattern.search(part.strip())
            if match:
                days_str, times_str = match.groups()

                # Split the days by ', ' and handle ranges like "Mon-Fri"
                days = days_str.split(', ')
                open_time_str, close_time_str = times_str.split('-')
                open_time = self.parse_time(open_time_str)
                close_time = self.parse_time(close_time_str)

                for day in days:
                    if '-' in day:  # Handle ranges like "Mon-Fri"
                        start_day, end_day = day.split('-')
                        day_range = list(day_map.keys())[list(day_map.keys()).index(start_day):list(day_map.keys()).index(end_day) + 1]
                    else:
                        day_range = [day]

                    # Map to the full day names and add to the hours_dict
                    for day_abbr in day_range:
                        full_day = day_map[day_abbr.strip()]
                        hours_dict[full_day].append((open_time, close_time))

        return hours_dict


    def check_open_hours(self, parsed_hours, datetime_obj):
        day_of_week = datetime_obj.strftime('%A')  # e.g., 'Monday'
        time_of_day = datetime_obj.time()

        if day_of_week in parsed_hours:
            for open_time, close_time in parsed_hours[day_of_week]:
                if open_time <= time_of_day <= close_time:
                    return True
        return False
