from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

BOOKING_CONFIRMATION_TEMPLATE = 'events/booking_confirmation_email.txt'


def send_booking_confirmation_email(ticket):
    """Send a booking confirmation email for a saved Ticket.

    Uses Person 2's template. Hamza should call this after a ticket is created.
    Leave exception handling to Person 5 so a send failure can be caught
    without blocking the booking.
    """
    attendee_email = (getattr(ticket.attendee, 'email', '') or '').strip()
    if not attendee_email:
        raise ValueError(
            'Cannot send booking confirmation without an attendee email.'
        )

    total_price = Decimal(ticket.event.price) * ticket.quantity
    rendered = render_to_string(
        BOOKING_CONFIRMATION_TEMPLATE,
        {
            'ticket': ticket,
            'total_price': total_price,
        },
    ).strip()

    lines = rendered.splitlines()
    if lines and lines[0].lower().startswith('subject:'):
        subject = lines[0].split(':', 1)[1].strip()
        body = '\n'.join(lines[1:]).lstrip('\n')
    else:
        subject = 'Your Eventify Booking Confirmation'
        body = rendered

    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[attendee_email],
    )
    message.send(fail_silently=False)
    return message
