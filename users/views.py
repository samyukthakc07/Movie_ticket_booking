from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from bookings.services import build_booking_request_key, create_pending_booking_for_user


def _safe_redirect_target(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if not next_url:
        return None

    allowed_hosts = {request.get_host()}
    public_app_host = urlparse(getattr(settings, 'PUBLIC_APP_BASE_URL', '')).netloc
    if public_app_host:
        allowed_hosts.add(public_app_host)

    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return next_url
    return None

def signup_view(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Movie Magic, {user.username}!")
            return redirect(_safe_redirect_target(request) or 'home')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = UserCreationForm()

    return render(request, 'users/signup.html', {
        'form': form,
        'next_url': next_url,
    })

def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')
    booking_notice = (request.POST.get('booking_required') or request.GET.get('booking_required')) == '1'
    show_id = request.POST.get('show_id') or request.GET.get('show_id', '')
    seat_ids = request.POST.get('seat_ids') or request.GET.get('seat_ids', '')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                seat_id_list = [seat_id.strip() for seat_id in seat_ids.split(',') if seat_id.strip()]
                booking_request_key = build_booking_request_key(request.session.session_key, show_id, seat_id_list)

                if booking_notice and show_id and seat_id_list:
                    try:
                        create_pending_booking_for_user(
                            user=user,
                            show_id=show_id,
                            seat_ids=seat_id_list,
                            request_key=booking_request_key,
                            allow_lock_creation=True,
                        )
                        messages.success(request, "Your reserved seats are ready for confirmation in My Bookings.")
                        return redirect('my_bookings')
                    except Exception as exc:
                        messages.error(request, str(exc))

                messages.success(request, f"Hello {username}, you are now logged in.")
                return redirect(_safe_redirect_target(request) or 'home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {
        'form': form,
        'next_url': next_url,
        'booking_notice': booking_notice,
        'show_id': show_id,
        'seat_ids': seat_ids,
    })

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')
