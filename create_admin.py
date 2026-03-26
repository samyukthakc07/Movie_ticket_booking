import os


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() == 'true'


def create_admin():
    from django.contrib.auth import get_user_model

    User = get_user_model()

    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    reset_password = _env_bool('DJANGO_SUPERUSER_RESET_PASSWORD', False)

    if not username or not password:
        print(
            "Skipping superuser bootstrap. Set DJANGO_SUPERUSER_USERNAME "
            "and DJANGO_SUPERUSER_PASSWORD to enable it."
        )
        return

    user = User.objects.filter(username=username).first()
    if not user:
        print(f"Creating superuser {username}...")
        User.objects.create_superuser(username=username, email=email, password=password)
        print("Superuser created successfully!")
        return

    changed_fields = []

    if email and user.email != email:
        user.email = email
        changed_fields.append('email')

    if not user.is_staff:
        user.is_staff = True
        changed_fields.append('is_staff')

    if not user.is_superuser:
        user.is_superuser = True
        changed_fields.append('is_superuser')

    if not user.is_active:
        user.is_active = True
        changed_fields.append('is_active')

    if reset_password:
        user.set_password(password)
        changed_fields.append('password')

    if changed_fields:
        print(f"Updating superuser {username}: {', '.join(changed_fields)}")
        user.save()
    else:
        print(
            f"Superuser {username} already exists. "
            "No changes were needed."
        )


def bootstrap_django():
    import django

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_booking_system.settings')

    # Make local script runs work even if a production secret key is not set.
    if 'DJANGO_SECRET_KEY' not in os.environ and 'DJANGO_DEBUG' not in os.environ:
        os.environ['DJANGO_DEBUG'] = 'True'

    django.setup()


if __name__ == "__main__":
    bootstrap_django()
    create_admin()
