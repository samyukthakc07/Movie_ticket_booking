from django.contrib import admin
from .models import Seat, SeatReservation, Booking

admin.site.register(Seat)
admin.site.register(SeatReservation)
admin.site.register(Booking)