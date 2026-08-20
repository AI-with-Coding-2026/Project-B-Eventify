import os
from decimal import Decimal
from pathlib import Path

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

BOOKING_CONFIRMATION_TEXT = 'events/booking_confirmation_email.txt'
BOOKING_CONFIRMATION_HTML = 'events/booking_confirmation_email.html'
LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'eventify_no_background.png'


def _absolute_url(path):
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return f"{settings.SITE_URL.rstrip('/')}/{path.lstrip('/')}"


def _get_logo_src():
    if LOGO_PATH.exists():
        return _absolute_url('/static/images/eventify_no_background.png')
    return ""


def _event_photo_url(url):
    """Use the real event photo (Cloudinary), in a size Gmail can load."""
    if not url or 'res.cloudinary.com' not in url:
        return url
    parsed = urlparse(url)
    if '/image/upload/' not in parsed.path:
        return url
    prefix, rest = parsed.path.split('/image/upload/', 1)
    if Path(rest).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        rest = f'{rest}.jpg'
    new_path = f'{prefix}/image/upload/w_800,c_limit,f_jpg,q_auto/{rest}'
    return urlunparse(parsed._replace(scheme='https', path=new_path))


def _get_event_image_src(event):
    """URL of the event's own photo, as shown on the event page."""
    image_field = getattr(event, 'image', None)
    if not image_field:
        return ''

    try:
        url = image_field.url
    except ValueError:
        return ''

    return _event_photo_url(_absolute_url(url))


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
    event_image_src = _get_event_image_src(ticket.event)
    context = {
        'ticket': ticket,
        'unit_price': unit_price,
        'total_price': total_price,
        'event_url': event_url,
        'logo_src': _get_logo_src(),
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
