from django.core.management.base import BaseCommand

from bookings.services import release_expired_locks


class Command(BaseCommand):
    help = "Release expired seat locks and mark stale pending bookings as expired."

    def handle(self, *args, **options):
        result = release_expired_locks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Released expired reservations. Locks={result['expired_locks']} Bookings={result['expired_bookings']}"
            )
        )

