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
BOOKING_CANCELLATION_TEXT = 'events/booking_cancellation_email.txt'
BOOKING_CANCELLATION_HTML = 'events/booking_cancellation_email.html'
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
    context = {
        'ticket': ticket,
        'unit_price': unit_price,
        'total_price': total_price,
        'event_url': event_url,
        'logo_src': _get_logo_src(),
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


def send_booking_cancellation_email(attendee, event, cancelled_quantity, remaining_quantity=0):
    """Send a booking cancellation confirmation email to an attendee."""
    attendee_email = (getattr(attendee, 'email', '') or '').strip()
    if not attendee_email:
        print("Cannot send booking cancellation email without an attendee email.")
        return None

    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("[WARNING] BREVO_API_KEY is missing. Cancellation email skipped.")
        return None

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    browse_events_url = f"{settings.SITE_URL}{reverse('event_list')}"
    context = {
        'attendee': attendee,
        'event': event,
        'cancelled_quantity': cancelled_quantity,
        'remaining_quantity': remaining_quantity,
        'browse_events_url': browse_events_url,
        'logo_src': _get_logo_src(),
    }

    rendered = render_to_string(BOOKING_CANCELLATION_TEXT, context).strip()
    lines = rendered.splitlines()
    if lines and lines[0].lower().startswith('subject:'):
        subject = lines[0].split(':', 1)[1].strip()
        text_body = '\n'.join(lines[1:]).lstrip('\n')
    else:
        subject = f'Your Eventify Booking Cancellation - {event.title}'
        text_body = rendered

    html_body = render_to_string(BOOKING_CANCELLATION_HTML, context)

    sender = {
        "name": "Eventify",
        "email": settings.DEFAULT_FROM_EMAIL,
    }
    to = [{"email": attendee_email, "name": attendee.username}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        text_content=text_body,
        html_content=html_body,
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Cancellation email sent successfully via Brevo API!")
        return response
    except ApiException as e:
        print(f"Failed to send cancellation email via Brevo API: {e}")
        return None
