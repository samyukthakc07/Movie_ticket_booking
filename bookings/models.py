from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from movies.models import Show


class Seat(models.Model):
    screen = models.ForeignKey('movies.Screen', on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)

    class Meta:
        indexes = [
            models.Index(fields=['screen', 'seat_number']),
        ]

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
        constraints = [
            models.UniqueConstraint(
                fields=['seat', 'show'],
                condition=Q(status__in=['locked', 'booked']),
                name='unique_active_seat_reservation',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'locked_until']),
            models.Index(fields=['show', 'status', 'locked_until']),
            models.Index(fields=['seat', 'show']),
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['booking_status', 'created_at']),
            models.Index(fields=['show', 'booking_status']),
        ]

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


class EmailDelivery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='email_deliveries')
    recipient_email = models.EmailField(db_index=True)
    template_name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    next_retry_at = models.DateTimeField(blank=True, null=True, db_index=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['booking', 'status']),
        ]

    def __str__(self):
        return f"EmailDelivery {self.id} - {self.recipient_email} - {self.status}"


class PaymentWebhookEvent(models.Model):
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ]

    provider = models.CharField(max_length=50, db_index=True)
    event_key = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100, db_index=True)
    signature = models.CharField(max_length=255, blank=True)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received', db_index=True)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.provider}:{self.event_type}:{self.event_key}"
