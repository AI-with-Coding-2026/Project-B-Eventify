import os
import ssl
from decimal import Decimal
from pathlib import Path

import requests
from decouple import config
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from requests.adapters import HTTPAdapter


BOOKING_CONFIRMATION_TEXT = (
    "events/booking_confirmation_email.txt"
)

BOOKING_CONFIRMATION_HTML = (
    "events/booking_confirmation_email.html"
)

CANCELLATION_TEXT = (
    "events/booking_cancellation_email.txt"
)

CANCELLATION_HTML = (
    "events/booking_cancellation_email.html"
)

LOGO_PATH = (
    Path(settings.BASE_DIR)
    / "static"
    / "images"
    / "eventify_no_background.png"
)


def _absolute_url(path):
    if not path:
        return ""

    if path.startswith("http://") or path.startswith("https://"):
        return path

    return (
        f"{settings.SITE_URL.rstrip('/')}/"
        f"{path.lstrip('/')}"
    )


def _get_logo_src():
    if LOGO_PATH.exists():
        return _absolute_url(
            "/static/images/eventify_no_background.png"
        )

    return ""


class _SystemCAAdapter(HTTPAdapter):
    """Use the OS certificate store so local antivirus HTTPS scanning works."""

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = ssl.create_default_context()
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = ssl.create_default_context()
        return super().proxy_manager_for(*args, **kwargs)


def _brevo_session():
    session = requests.Session()
    adapter = _SystemCAAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_brevo_api_key():
    return (
        config(
            "BREVO_API_KEY",
            default=""
        )
        or os.environ.get(
            "BREVO_API_KEY",
            ""
        )
    ).strip()


def _send_brevo_email(
    *,
    api_key,
    sender,
    to,
    subject,
    text_body,
    html_body,
):
    """
    Send an email directly through Brevo's REST API.
    """

    if not api_key:
        raise ValueError(
            "BREVO_API_KEY is missing."
        )

    if not sender or not sender.get("email"):
        raise ValueError(
            "DEFAULT_FROM_EMAIL is missing."
        )

    if not to:
        raise ValueError(
            "No recipient email address was provided."
        )

    payload = {
        "sender": sender,
        "to": to,
        "subject": subject,
        "textContent": text_body,
        "htmlContent": html_body,
    }

    response = _brevo_session().post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    try:
        return response.json()
    except ValueError:
        return {
            "status_code": response.status_code,
            "response": response.text,
        }


def _send_ticket_email(
    *,
    ticket,
    text_template,
    html_template,
    default_subject,
):
    """
    Common email-sending logic used by both
    booking confirmation and cancellation emails.
    """

    attendee = getattr(
        ticket,
        "attendee",
        None
    )

    attendee_email = (
        getattr(
            attendee,
            "email",
            ""
        )
        or ""
    ).strip()

    if not attendee_email:
        raise ValueError(
            "Cannot send email because the attendee "
            "does not have an email address."
        )

    api_key = _get_brevo_api_key()

    if not api_key:
        raise ValueError(
            "BREVO_API_KEY is missing. "
            "Email cannot be sent."
        )

    default_from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        ""
    )

    if not default_from_email:
        raise ValueError(
            "DEFAULT_FROM_EMAIL is missing. "
            "Email cannot be sent."
        )

    event = ticket.event

    unit_price = Decimal(
        str(event.price)
    )

    total_price = (
        unit_price * ticket.quantity
    )

    event_url = (
        f"{settings.SITE_URL.rstrip('/')}"
        f"{reverse('event_detail', args=[event.pk])}"
    )

    context = {
        "ticket": ticket,
        "unit_price": unit_price,
        "total_price": total_price,
        "event_url": event_url,
        "logo_src": _get_logo_src(),
    }

    rendered = render_to_string(
        text_template,
        context
    ).strip()

    lines = rendered.splitlines()

    if (
        lines
        and lines[0].lower().startswith("subject:")
    ):
        subject = (
            lines[0]
            .split(":", 1)[1]
            .strip()
        )

        text_body = (
            "\n".join(lines[1:])
            .lstrip("\n")
        )
    else:
        subject = default_subject
        text_body = rendered

    html_body = render_to_string(
        html_template,
        context
    )

    sender = {
        "name": "Eventify",
        "email": default_from_email,
    }

    attendee_name = (
        getattr(
            attendee,
            "username",
            ""
        )
        or attendee_email
    )

    to = [
        {
            "email": attendee_email,
            "name": attendee_name,
        }
    ]

    return _send_brevo_email(
        api_key=api_key,
        sender=sender,
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_booking_confirmation_email(ticket):
    """
    Send a booking confirmation email for a saved Ticket.
    """

    try:
        response = _send_ticket_email(
            ticket=ticket,
            text_template=BOOKING_CONFIRMATION_TEXT,
            html_template=BOOKING_CONFIRMATION_HTML,
            default_subject=(
                "Your Eventify Booking Confirmation"
            ),
        )

        print(
            "Confirmation email sent successfully "
            "via Brevo API!"
        )

        return response

    except requests.RequestException as e:
        print(
            "FAILED TO SEND BOOKING CONFIRMATION "
            "EMAIL VIA BREVO API"
        )

        print(
            f"Brevo error: {e}"
        )

        if getattr(e, "response", None) is not None:
            print(
                "Brevo status code: "
                f"{e.response.status_code}"
            )

            print(
                "Brevo response: "
                f"{e.response.text}"
            )

        raise

    except Exception as e:
        print(
            "BOOKING CONFIRMATION EMAIL ERROR: "
            f"{e}"
        )

        raise


def send_booking_cancellation_email(ticket):
    """
    Send a booking cancellation confirmation email
    before the Ticket object is deleted.
    """

    try:
        response = _send_ticket_email(
            ticket=ticket,
            text_template=CANCELLATION_TEXT,
            html_template=CANCELLATION_HTML,
            default_subject=(
                "Your Eventify Booking Cancellation Confirmation"
            ),
        )

        print(
            "Cancellation confirmation email "
            "sent successfully via Brevo API!"
        )

        return response

    except requests.RequestException as e:
        print(
            "FAILED TO SEND CANCELLATION EMAIL "
            "VIA BREVO API"
        )

        print(
            f"Brevo error: {e}"
        )

        if getattr(e, "response", None) is not None:
            print(
                "Brevo status code: "
                f"{e.response.status_code}"
            )

            print(
                "Brevo response: "
                f"{e.response.text}"
            )

        raise

    except Exception as e:
        print(
            "CANCELLATION EMAIL ERROR: "
            f"{e}"
        )

        raise