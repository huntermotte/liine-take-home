import re
from datetime import datetime, time, timedelta
from rest_framework import generics, status
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from .models import Restaurant
from .serializers import RestaurantSerializer


class RestaurantListAPIView(generics.ListAPIView):
    serializer_class = RestaurantSerializer

    def get(self, request, *args, **kwargs):
        """
        Returns a list of restaurant names that are open at a specific datetime.

        The view filters restaurants based on a `datetime` query parameter provided in the URL.
        The `datetime` parameter must include both date and time in ISO 8601 format (e.g., '2024-08-25T17:00:00').
        If the `datetime` parameter is missing, or if it lacks time information, an error response is returned.
        """
        queryset = Restaurant.objects.all()
        datetime_str = self.request.query_params.get('datetime', None)

        validation_error = self.validate_datetime_str(datetime_str)
        if validation_error:
            return Response({"error": validation_error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            datetime_obj = parse_datetime(datetime_str)
            if datetime_obj is None:
                raise ValueError("Invalid datetime format. Please use value that specifies a date and a time.")

            open_restaurant_names = [
                restaurant.name for restaurant in queryset
                if self.is_open(restaurant, datetime_obj)
            ]
            return Response({"open_restaurants": open_restaurant_names}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def validate_datetime_str(self, datetime_str):
        """Validate the datetime string and ensure it includes time information."""
        if not datetime_str:
            return "A 'datetime' query parameter is required."

        if 'T' not in datetime_str or len(datetime_str.split('T')[1]) == 0:
            return "The provided datetime is missing time information. Please include both date and time."

        return None

    def is_open(self, restaurant, datetime_obj):
        """Determine if the restaurant is open at the given datetime."""
        parsed_hours = self.parse_hours(restaurant.hours)
        return self.check_open_hours(parsed_hours, datetime_obj)

    def parse_time(self, time_str):
        """Convert time string like '11:00 am' or '12:30 pm' or '10 pm' into a datetime.time object."""
        try:
            return datetime.strptime(time_str.strip(), '%I:%M %p').time()
        except ValueError:
            return datetime.strptime(time_str.strip(), '%I %p').time()

    def parse_hours(self, hours_str):
        """Parse the hours string into a structured format."""
        day_map = {
            'Mon': 'Monday', 'Tues': 'Tuesday', 'Wed': 'Wednesday', 'Thu': 'Thursday',
            'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'
        }
        hours_dict = {day: [] for day in day_map.values()}

        # Regex to find day ranges and times
        # 1. A-Za-z: All alphabetic characters.
        # 2. ,: The comma character to separate days.
        # 3. \s: Whitespace (space, tab, etc.).
        # 4. -: The hyphen character at the end of the class
        day_time_pattern = re.compile(r'([A-Za-z,\s-]+)\s+([\d:\sampm-]+)')

        for part in hours_str.split('/'):
            match = day_time_pattern.search(part.strip())
            if match:
                days_str, times_str = match.groups()
                open_time, close_time = map(self.parse_time, times_str.split('-'))

                day_range = self.expand_day_range(days_str, day_map)
                for full_day in day_range:
                    if close_time == time(0, 0):
                        close_time = time(23, 59)  # Treat midnight as end of the day
                    hours_dict[full_day].append((open_time, close_time))

        return hours_dict

    def expand_day_range(self, days_str, day_map):
        """Expand a day range like 'Mon-Fri' into a list of full day names."""
        days = days_str.split(', ')
        expanded_days = []
        for day in days:
            if '-' in day:
                start_day, end_day = day.split('-')
                expanded_days.extend(
                    list(day_map.values())[
                    list(day_map.keys()).index(start_day):list(day_map.keys()).index(end_day) + 1]
                )
            else:
                expanded_days.append(day_map[day.strip()])
        return expanded_days

    def check_open_hours(self, parsed_hours, datetime_obj):
        """Check if a restaurant is open on the given datetime."""
        day_of_week = datetime_obj.strftime('%A')
        time_of_day = datetime_obj.time()

        # Check if there are hours listed for the current day
        if day_of_week not in parsed_hours or not parsed_hours[day_of_week]:
            return False

        # Check if the restaurant is open during the current day's hours
        if self.is_within_open_hours(parsed_hours[day_of_week], time_of_day):
            return True

        # Check for the previous day's late night hours (extending past midnight)
        previous_day = (datetime_obj - timedelta(days=1)).strftime('%A')
        if previous_day in parsed_hours and self.is_within_open_hours(parsed_hours[previous_day], time_of_day):
            return True

        return False

    def is_within_open_hours(self, hours_list, time_of_day):
        """Check if the given time is within any open hours."""
        for open_time, close_time in hours_list:
            if close_time <= open_time:
                if open_time <= time_of_day or time_of_day <= close_time:
                    return True
            elif open_time <= time_of_day <= close_time:
                return True
        return False
