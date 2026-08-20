from decimal import Decimal
from email.mime.image import MIMEImage
from email.utils import formataddr
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

BOOKING_CONFIRMATION_TEXT = 'events/booking_confirmation_email.txt'
BOOKING_CONFIRMATION_HTML = 'events/booking_confirmation_email.html'
LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'eventify_no_background.png'


def _attach_eventify_logo(message):
    if not LOGO_PATH.exists():
        return
    with LOGO_PATH.open('rb') as logo_file:
        logo = MIMEImage(logo_file.read())
    logo.add_header('Content-ID', '<eventify-logo>')
    logo.add_header('Content-Disposition', 'inline', filename=LOGO_PATH.name)
    message.attach(logo)


def send_booking_confirmation_email(ticket):
    """Send a booking confirmation email for a saved Ticket."""
    attendee_email = (getattr(ticket.attendee, 'email', '') or '').strip()
    if not attendee_email:
        raise ValueError(
            'Cannot send booking confirmation without an attendee email.'
        )

    total_price = Decimal(ticket.event.price) * ticket.quantity
    event_url = f"{settings.SITE_URL}{reverse('event_detail', args=[ticket.event.pk])}"
    context = {
        'ticket': ticket,
        'total_price': total_price,
        'event_url': event_url,
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

    import uuid
    msg_id = f"<{uuid.uuid4()}@eventify.local>"

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=formataddr(('Eventify', sender_address)),
        to=[attendee_email],
        headers={'Message-ID': msg_id},
    )
    message.attach_alternative(html_body, 'text/html')
    _attach_eventify_logo(message)
    message.send(fail_silently=False)
    return message
