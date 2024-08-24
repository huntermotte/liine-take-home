from rest_framework import generics
from .models import Restaurant
from .serializers import RestaurantSerializer

class RestaurantListAPIView(generics.ListAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
