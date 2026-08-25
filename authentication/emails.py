import requests
from django.conf import settings
from django.template.loader import render_to_string

from events.emails import (
    _get_brevo_api_key,
    _get_logo_src,
    _send_brevo_email,
)


VERIFICATION_TEXT = "authentication/verification_email.txt"
VERIFICATION_HTML = "authentication/verification_email.html"
DEFAULT_SUBJECT = "Verify your Eventify email address"


def send_verification_email(user, verification_url):
    """
    Send an email-verification message for a newly created account.

    The caller must supply the absolute verification_url. This function
    does not generate tokens or change user state.
    """

    user_email = (getattr(user, "email", "") or "").strip()

    if not user_email:
        raise ValueError(
            "Cannot send email because the user "
            "does not have an email address."
        )

    try:
        api_key = _get_brevo_api_key()

        if not api_key:
            raise ValueError(
                "BREVO_API_KEY is missing. "
                "Email cannot be sent."
            )

        default_from_email = getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            "",
        )

        if not default_from_email:
            raise ValueError(
                "DEFAULT_FROM_EMAIL is missing. "
                "Email cannot be sent."
            )

        context = {
            "user": user,
            "verification_url": verification_url,
            "logo_src": _get_logo_src(),
        }

        rendered = render_to_string(
            VERIFICATION_TEXT,
            context,
        ).strip()

        lines = rendered.splitlines()

        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            text_body = "\n".join(lines[1:]).lstrip("\n")
        else:
            subject = DEFAULT_SUBJECT
            text_body = rendered

        html_body = render_to_string(
            VERIFICATION_HTML,
            context,
        )

        username = getattr(user, "username", "") or user_email

        response = _send_brevo_email(
            api_key=api_key,
            sender={
                "name": "Eventify",
                "email": default_from_email,
            },
            to=[
                {
                    "email": user_email,
                    "name": username,
                }
            ],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        print(
            "Verification email sent successfully "
            "via Brevo API!"
        )

        return response

    except requests.RequestException as e:
        print(
            "FAILED TO SEND VERIFICATION "
            "EMAIL VIA BREVO API"
        )
        print(f"Brevo error: {e}")

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
        print(f"VERIFICATION EMAIL ERROR: {e}")
        raise
