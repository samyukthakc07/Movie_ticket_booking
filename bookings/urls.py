from django.urls import path
from .views import reserve_seat, seat_layout, create_booking, checkout_summary, payment_success, payment_cancel, seat_selection, my_bookings, confirm_booking, cancel_booking

urlpatterns = [
    path('reserve-seat/', reserve_seat),
    path('seat-layout/', seat_layout),
    path('create-booking/', create_booking),
    path('checkout/<int:booking_id>/', checkout_summary),
    path('payment-success/', payment_success, name='payment_success'),
    path('payment-cancel/', payment_cancel, name='payment_cancel'),
    path('seats/', seat_selection),
    path('my-bookings/', my_bookings, name='my_bookings'),
    path('confirm-booking/<int:booking_id>/', confirm_booking, name='confirm_booking'),
    path('cancel-booking/<int:booking_id>/', cancel_booking, name='cancel_booking'),
]