from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


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

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
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
    })

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')
