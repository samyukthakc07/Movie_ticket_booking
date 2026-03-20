from django.core.management.base import BaseCommand

from bookings.services import send_due_email_deliveries


class Command(BaseCommand):
    help = "Process queued booking confirmation emails."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=25)

    def handle(self, *args, **options):
        result = send_due_email_deliveries(batch_size=options['batch_size'])
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed email queue. Sent={result['sent']} Failed={result['failed']}"
            )
        )

