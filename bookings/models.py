from django.db import models
from django.contrib.auth.models import User
from movies.models import Show


class Seat(models.Model):
    screen = models.ForeignKey('movies.Screen', on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)

    def __str__(self):
        return self.seat_number


class SeatReservation(models.Model):
    STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('booked', 'Booked'),
        ('expired', 'Expired')
    ]

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    locked_until = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('seat', 'show', 'status') # simplified for brevity, but logically locked/booked should be unique
        indexes = [
            models.Index(fields=['status', 'locked_until']),
        ]

    def __str__(self):
        return f"{self.seat.seat_number} - {self.status}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=200, blank=True, null=True, db_index=True)
    booking_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id} - {self.user.username}"


class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment_details')
    stripe_charge_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.stripe_charge_id} - {self.status}"