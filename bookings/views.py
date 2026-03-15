from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import Booking, SeatReservation, Seat
from movies.models import Show
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@api_view(['POST'])
def reserve_seat(request):
    """
    Concurrency-safe seat reservation with row-level locking.
    Prevents double booking selection within milliseconds.
    """
    seat_id = request.data.get("seat_id")
    show_id = request.data.get("show_id")
    user_id = request.data.get("user_id")

    # Use atomic transaction with select_for_update for row-level locking
    with transaction.atomic():
        # Clean up expired locks first (can be done here or in background)
        # release_expired_locks() is called globally but better to keep it focused
        
        try:
            # Clean up expired locks first
            release_expired_locks()
            
            # Check if seat is already occupied by a valid 'booked' or 'locked' reservation
            existing = SeatReservation.objects.select_for_update().filter(
                seat_id=seat_id,
                show_id=show_id
            ).filter(
                Q(status='booked') | 
                Q(status='locked', locked_until__gt=timezone.now())
            ).exists()

            if existing:
                return Response({
                    "status": "error",
                    "message": "Seat already reserved or selection in progress."
                }, status=400)

            # Clear any stale 'locked' records for this seat/show to avoid UniqueConstraint errors
            SeatReservation.objects.filter(
                seat_id=seat_id, 
                show_id=show_id, 
                status='locked'
            ).delete()

            lock_time = timezone.now() + timedelta(minutes=2)

            reservation = SeatReservation.objects.create(
                seat_id=seat_id,
                show_id=show_id,
                user_id=user_id,
                status="locked",
                locked_until=lock_time
            )

            return Response({
                "status": "success",
                "message": "Seat locked for 2 minutes.",
                "locked_until": lock_time
            })
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)
    
def release_expired_locks():
    SeatReservation.objects.filter(
        status="locked",
        locked_until__lt=timezone.now()
    ).delete()


@api_view(['GET'])
def seat_layout(request):
    """
    TASK 5: Concurrency-Safe Seat Reservation.
    Optimization: Fetches all seats and relevant reservations in minimal queries.
    Strategy: 
    - We use a single query to fetch all reservations for this show that are either 'booked' or 'locked' (and not expired).
    - Map these to seat IDs for O(1) lookup during layout generation.
    - Consistency Model: Pessimistic locking (select_for_update) is used during reservation to ensure atomicity.
    """
    show_id = request.GET.get("show_id")
    if not show_id:
        return Response({"error": "show_id is required"}, status=400)

    # Explicitly release expired locks before querying
    release_expired_locks()

    # Get active reservations (locked or booked)
    # We order by -status to ensure 'locked' comes after 'booked' if we were to have both (B > L)
    # But better to just be explicit in the map.
    active_reservations = SeatReservation.objects.filter(
        show_id=show_id,
        status__in=['locked', 'booked']
    ).values('seat_id', 'status')

    reservation_map = {}
    for res in active_reservations:
        sid, status = res['seat_id'], res['status']
        if status == 'booked' or sid not in reservation_map:
            reservation_map[sid] = status

    # Get all seats for the screen associated with this show
    show = Show.objects.get(id=show_id)
    seats = Seat.objects.filter(screen=show.screen)

    seat_data = []
    for seat in seats:
        status = reservation_map.get(seat.id, "available")
        seat_data.append({
            "seat_id": seat.id,
            "seat_number": seat.seat_number,
            "status": status
        })

    return Response({
        "show_title": show.movie.title,
        "theater": show.screen.theater.name,
        "show_time": show.show_time,
        "price": show.price,
        "seats": seat_data
    })


@api_view(['POST'])
def create_booking(request):
    """
    TASK 4: Payment Gateway Integration.
    Step 1: Create a 'pending' booking after seat selection.
    Idempotency: Uses client-provided session tokens if necessary, or simply relies on unique seat-show locks.
    """
    user_id = request.data.get("user_id", 1) # Mock User
    show_id = request.data.get("show_id")
    seat_ids = request.data.get("seat_ids")

    with transaction.atomic():
        show = Show.objects.get(id=show_id)
        
        # Verify seats are still locked for this user
        valid_reservations = SeatReservation.objects.filter(
            show_id=show_id,
            seat_id__in=seat_ids,
            user_id=user_id,
            status='locked',
            locked_until__gt=timezone.now()
        ).count()

        if valid_reservations != len(seat_ids):
            return Response({"error": "Some seat reservations expired. Please try again."}, status=400)

        booking = Booking.objects.create(
            user_id=user_id,
            show=show,
            total_amount=show.price * len(seat_ids),
            booking_status='pending'
        )
        booking.seats.set(seat_ids)
        
        return Response({
            "status": "success",
            "booking_id": booking.id,
            "total_amount": booking.total_amount
        })

def checkout_summary(request, booking_id):
    from django.conf import settings
    booking = Booking.objects.get(id=booking_id)
    return render(request, "checkout.html", {
        "booking": booking,
        "stripe_public_key": getattr(settings, 'STRIPE_PUBLIC_KEY', 'pk_test_sample')
    })

def payment_success(request):
    return render(request, "payment_result.html", {"status": "success"})

def payment_cancel(request):
    return render(request, "payment_result.html", {"status": "cancelled"})

def seat_selection(request):
    return render(request,"seat_selection.html")

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "my_bookings.html", {"bookings": bookings})

@login_required
@api_view(['POST'])
def cancel_booking(request, booking_id):
    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(id=booking_id, user=request.user)
            if booking.booking_status == 'cancelled':
                return Response({"error": "Booking already cancelled"}, status=400)
            
            booking.booking_status = 'cancelled'
            booking.save()
            
            # Release reservations
            SeatReservation.objects.filter(
                show=booking.show,
                seat__in=booking.seats.all(),
                user=request.user
            ).update(status='expired')
            
            return Response({"status": "success", "message": "Booking cancelled successfully"})
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@login_required
@api_view(['POST'])
def confirm_booking(request, booking_id):
    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(id=booking_id, user=request.user)
            if booking.booking_status == 'confirmed':
                return Response({"error": "Booking already confirmed"}, status=400)
            
            booking.booking_status = 'confirmed'
            booking.save()
            
            # Update reservations to booked
            SeatReservation.objects.filter(
                show=booking.show,
                seat__in=booking.seats.all(),
                user=request.user
            ).update(status='booked')
            
            return Response({"status": "success", "message": "Booking confirmed successfully"})
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

