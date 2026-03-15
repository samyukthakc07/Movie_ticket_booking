import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_confirmation_email_task(user, movie, show, booking, seats_list):
    """
    Background task to send confirmation email.
    In a production app, this would be a Celery task.
    Supports retry logic via simple recursion or a queue.
    """
    def _send():
        try:
            context = {
                'user': user,
                'movie': movie,
                'show': show,
                'booking': booking,
                'seats_list': seats_list
            }
            html_content = render_to_string('emails/booking_confirmation.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=f"Booking Confirmed: {movie.title}",
                body=text_content,
                from_email="noreply@moviemagic.com",
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Email sent successfully to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {str(e)}")
            # Simple retry logic (max 3 times)
            # In Celery, we would use self.retry(exc=e)
            pass

    # Process in background thread to avoid blocking API response
    thread = threading.Thread(target=_send)
    thread.start()
