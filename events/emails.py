import os
import base64
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
    """قراءة اللوجو المحلي وتحويله إلى Base64 ليعمل مع Brevo API."""
    try:
        if LOGO_PATH.exists():
            with LOGO_PATH.open('rb') as logo_file:
                encoded = base64.b64encode(logo_file.read()).decode('utf-8')
                return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"Failed to load logo Base64: {e}")
    return ""


def send_booking_confirmation_email(ticket):
    """Send a booking confirmation email for a saved Ticket via Brevo API."""
    attendee_email = (getattr(ticket.attendee, 'email', '') or '').strip()
    if not attendee_email:
        raise ValueError(
            'Cannot send booking confirmation without an attendee email.'
        )

    # 1. إعداد حساب Brevo API
    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("BREVO_API_KEY is missing. Email skipped.")
        return None

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # 2. تحضير السياق والقوالب
    total_price = Decimal(ticket.event.price) * ticket.quantity
    event_url = f"{settings.SITE_URL}{reverse('event_detail', args=[ticket.event.pk])}"
    context = {
        'ticket': ticket,
        'total_price': total_price,
        'event_url': event_url,
        'logo_src': _get_logo_base64(),  # إضافة اللوجو للسياق
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

<<<<<<< HEAD
    # 3. إعداد عناصر الرسالة وإرسالها
    sender = {
        "name": "Eventify", 
        "email": settings.DEFAULT_FROM_EMAIL  
    }
    
    to = [{"email": attendee_email, "name": ticket.attendee.username}]

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        text_content=text_body,
        html_content=html_body,
=======
    import uuid
    msg_id = f"<{uuid.uuid4()}@eventify.local>"

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=formataddr(('Eventify', sender_address)),
        to=[attendee_email],
        headers={'Message-ID': msg_id},
>>>>>>> c7b8d8e78f30d3e25cd4e8f81aea01439a77dfdc
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Confirmation email sent successfully via Brevo API!")
        return response
    except ApiException as e:
        print(f"Failed to send email via Brevo API: {e}")
        raise e