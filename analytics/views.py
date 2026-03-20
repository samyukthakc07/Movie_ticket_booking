from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour
from django.shortcuts import render
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from bookings.models import Booking
from movies.models import Show


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    """
    Cached analytics built from database-level aggregations only.
    """
    stats = cache.get('admin_dashboard_stats')
    if stats:
        return Response(stats)

    now = timezone.now()
    revenue_periods = {
        'daily': now - timedelta(days=1),
        'weekly': now - timedelta(days=7),
        'monthly': now - timedelta(days=30),
    }

    revenue = {
        label: Booking.objects.filter(
            booking_status='confirmed',
            created_at__gte=start,
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        for label, start in revenue_periods.items()
    }

    popular_movies = Booking.objects.filter(
        booking_status='confirmed',
    ).values(
        'show__movie__title',
    ).annotate(
        bookings_count=Count('id'),
    ).order_by('-bookings_count', 'show__movie__title')[:10]

    peak_hours = Booking.objects.filter(
        booking_status='confirmed',
    ).annotate(
        hour=ExtractHour('created_at'),
    ).values('hour').annotate(
        total=Count('id'),
    ).order_by('-total', 'hour')

    total_bookings = Booking.objects.count()
    cancelled_bookings = Booking.objects.filter(booking_status='cancelled').count()
    cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings else 0

    theatre_rows = list(
        Show.objects.values(
            'screen__theater__name',
        ).annotate(
            total_capacity=Sum('screen__total_seats'),
            booked_seats=Count('booking__seats', filter=Q(booking__booking_status='confirmed')),
        )
    )
    theatre_performance = []
    for row in theatre_rows:
        total_capacity = row['total_capacity'] or 0
        booked_seats = row['booked_seats'] or 0
        occupancy_rate = round((booked_seats / total_capacity * 100), 2) if total_capacity else 0
        theatre_performance.append({
            'theatre': row['screen__theater__name'],
            'booked_seats': booked_seats,
            'total_capacity': total_capacity,
            'occupancy_rate': occupancy_rate,
        })
    theatre_performance.sort(key=lambda item: (-item['occupancy_rate'], item['theatre']))

    average_occupancy = round(
        sum(item['occupancy_rate'] for item in theatre_performance) / len(theatre_performance),
        2,
    ) if theatre_performance else 0

    stats = {
        'total_revenue': revenue['monthly'],
        'revenue_breakdown': revenue,
        'popular_movies': [
            {'movie': row['show__movie__title'], 'count': row['bookings_count']}
            for row in popular_movies
        ],
        'peak_hours': list(peak_hours),
        'cancellation_rate': round(cancellation_rate, 2),
        'average_occupancy': average_occupancy,
        'theatre_performance': theatre_performance[:10],
    }

    cache.set('admin_dashboard_stats', stats, 300)
    return Response(stats)


@staff_member_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')
