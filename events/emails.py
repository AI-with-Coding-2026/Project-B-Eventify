from decimal import Decimal
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

BOOKING_CONFIRMATION_TEXT = 'events/booking_confirmation_email.txt'
BOOKING_CONFIRMATION_HTML = 'events/booking_confirmation_email.html'


def send_booking_confirmation_email(ticket):
    """Send a booking confirmation email for a saved Ticket."""
    attendee_email = (getattr(ticket.attendee, 'email', '') or '').strip()
    if not attendee_email:
        raise ValueError(
            'Cannot send booking confirmation without an attendee email.'
        )

    total_price = Decimal(ticket.event.price) * ticket.quantity
    context = {
        'ticket': ticket,
        'total_price': total_price,
    }

    rendered = render_to_string(BOOKING_CONFIRMATION_TEXT, context).strip()
    lines = rendered.splitlines()
    if lines and lines[0].lower().startswith('subject:'):
        subject = lines[0].split(':', 1)[1].strip()
        text_body = '\n'.join(lines[1:]).lstrip('\n')
    else:
        subject = 'Your Eventify Booking Confirmation'
        text_body = rendered

    html_body = render_to_string(BOOKING_CONFIRMATION_HTML, context)
    sender_address = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=formataddr(('Eventify', sender_address)),
        to=[attendee_email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
    return message
