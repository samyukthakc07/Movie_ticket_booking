import os
import django
from django.contrib.auth import get_user_model

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_booking_system.settings')
django.setup()

def create_admin():
    User = get_user_model()
    
    # Get values from env vars if they exist, otherwise use defaults
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser {username}...")
        User.objects.create_superuser(username=username, email=email, password=password)
        print("Superuser created successfully!")
    else:
        print(f"Superuser {username} already exists.")

if __name__ == "__main__":
    create_admin()
