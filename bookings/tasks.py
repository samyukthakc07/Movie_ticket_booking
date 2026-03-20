import logging

from .services import queue_booking_confirmation_email, send_due_email_deliveries

logger = logging.getLogger(__name__)

def send_confirmation_email_task(user, movie, show, booking, seats_list):
    """
    Compatibility wrapper used by existing views.
    The actual delivery is queue-based and processed by a worker command.
    """
    logger.info("Queueing booking confirmation email for booking %s", booking.id)
    return queue_booking_confirmation_email(booking)


def process_email_queue(batch_size=25):
    return send_due_email_deliveries(batch_size=batch_size)
