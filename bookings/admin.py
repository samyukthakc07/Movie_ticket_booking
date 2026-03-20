from django.contrib import admin
from .models import Booking, EmailDelivery, PaymentWebhookEvent, Seat, SeatReservation

admin.site.register(Seat)
admin.site.register(SeatReservation)
admin.site.register(Booking)
admin.site.register(EmailDelivery)
admin.site.register(PaymentWebhookEvent)
