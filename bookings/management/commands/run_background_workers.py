import time

from django.core.management.base import BaseCommand

from bookings.services import release_expired_locks, send_due_email_deliveries


class Command(BaseCommand):
    help = "Run lightweight background workers for email queue processing and seat lock expiry."

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=15)
        parser.add_argument('--batch-size', type=int, default=25)
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        interval = max(options['interval'], 5)
        batch_size = max(options['batch_size'], 1)

        while True:
            release_result = release_expired_locks()
            email_result = send_due_email_deliveries(batch_size=batch_size)
            self.stdout.write(
                f"Background cycle complete. Expired locks={release_result['expired_locks']} "
                f"expired bookings={release_result['expired_bookings']} "
                f"emails sent={email_result['sent']} emails failed={email_result['failed']}"
            )

            if options['once']:
                break
            time.sleep(interval)
