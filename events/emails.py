import base64
import mimetypes
import os
from decimal import Decimal
from pathlib import Path

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

BOOKING_CONFIRMATION_TEXT = 'events/booking_confirmation_email.txt'
BOOKING_CONFIRMATION_HTML = 'events/booking_confirmation_email.html'
LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'eventify_no_background.png'


def _get_logo_base64():
    """Read the local logo and convert it to Base64 for the Brevo API."""
    try:
        if LOGO_PATH.exists():
            with LOGO_PATH.open('rb') as logo_file:
                encoded = base64.b64encode(logo_file.read()).decode('utf-8')
                return f"data:image/png;base64,{encoded}"
    except OSError:
        return ""
    return ""


def _get_event_image_data_uri(event):
    """Embed the event picture so Gmail can show it in the confirmation email."""
    image_field = getattr(event, 'image', None)
    if not image_field:
        return ''

    try:
        with image_field.open('rb') as image_file:
            content = image_file.read()
    except (OSError, ValueError, FileNotFoundError):
        return ''

    if not content:
        return ''

    filename = Path(getattr(image_field, 'name', 'event.jpg')).name
    content_type, _ = mimetypes.guess_type(filename)
    mime = content_type if content_type and content_type.startswith('image/') else 'image/jpeg'
    encoded = base64.b64encode(content).decode('utf-8')
    return f'data:{mime};base64,{encoded}'


def send_booking_confirmation_email(ticket):
    """Send a booking confirmation email for a saved Ticket via Brevo API."""
    attendee_email = (getattr(ticket.attendee, 'email', '') or '').strip()
    if not attendee_email:
        raise ValueError(
            'Cannot send booking confirmation without an attendee email.'
        )

    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("BREVO_API_KEY is missing. Email skipped.")
        return None

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    unit_price = Decimal(ticket.event.price)
    total_price = unit_price * ticket.quantity
    event_url = f"{settings.SITE_URL}{reverse('event_detail', args=[ticket.event.pk])}"
    event_image_src = _get_event_image_data_uri(ticket.event)
    context = {
        'ticket': ticket,
        'unit_price': unit_price,
        'total_price': total_price,
        'event_url': event_url,
        'logo_src': _get_logo_base64(),
        'event_image_src': event_image_src,
        'has_event_image': bool(event_image_src),
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

    sender = {
        "name": "Eventify",
        "email": settings.DEFAULT_FROM_EMAIL,
    }
    to = [{"email": attendee_email, "name": ticket.attendee.username}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        text_content=text_body,
        html_content=html_body,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Confirmation email sent successfully via Brevo API!")
        return response
    except ApiException as e:
        print(f"Failed to send email via Brevo API: {e}")
        raise e
