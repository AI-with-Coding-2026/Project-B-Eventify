import os
from pathlib import Path
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


VERIFICATION_TEXT = "authentication/verification_email.txt"
VERIFICATION_HTML = "authentication/verification_email.html"
DEFAULT_SUBJECT = "Verify your Eventify email address"

PASSWORD_RESET_TEXT = "authentication/password_reset_email.txt"
PASSWORD_RESET_HTML = "authentication/password_reset_email.html"
DEFAULT_RESET_SUBJECT = "Reset your Eventify password"

LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'eventify_no_background.png'


def _get_logo_src():
    if LOGO_PATH.exists():
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        return f"{site_url}/static/images/eventify_no_background.png"
    return ""


def send_verification_email(user, verification_url):
    """
    Send an email-verification message for a newly created account via Brevo API,
    falling back to Django's standard email backend if needed.
    """
    user_email = (getattr(user, "email", "") or "").strip()
    if not user_email:
        raise ValueError("Cannot send email because the user does not have an email address.")

    context = {
        "user": user,
        "verification_url": verification_url,
        "logo_src": _get_logo_src(),
    }

    rendered = render_to_string(VERIFICATION_TEXT, context).strip()
    lines = rendered.splitlines()

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        text_body = "\n".join(lines[1:]).lstrip("\n")
    else:
        subject = DEFAULT_SUBJECT
        text_body = rendered

    html_body = render_to_string(VERIFICATION_HTML, context)

    api_key = getattr(settings, "BREVO_API_KEY", "") or os.environ.get("BREVO_API_KEY", "")

    if api_key:
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = api_key
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            sender = {
                "name": "Eventify",
                "email": settings.DEFAULT_FROM_EMAIL,
            }
            username = getattr(user, "username", "") or user_email
            to = [{"email": user_email, "name": username}]

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject=subject,
                text_content=text_body,
                html_content=html_body,
            )

            response = api_instance.send_transac_email(send_smtp_email)
            print(f"Verification email sent successfully via Brevo API to {user_email}!")
            return response
        except ApiException as e:
            print(f"Brevo API error sending verification email: {e}")

    # Fallback to Django Email Backend
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=f"Eventify <{settings.DEFAULT_FROM_EMAIL}>",
            to=[user_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        print(f"Verification email sent via Django email backend to {user_email}.")
    except Exception as fallback_err:
        print("==================================================")
        print(f"[WARNING] Verification email fallback link for {user_email}:")
        print(f"Verification URL: {verification_url}")
        print(f"Error: {fallback_err}")
        print("==================================================")

    return None


def send_password_reset_email(user, reset_url):
    """
    Send a password reset email to the user via Brevo API with fallback.
    """
    user_email = (getattr(user, "email", "") or "").strip()
    if not user_email:
        raise ValueError("Cannot send password reset email because user has no email address.")

    context = {
        "user": user,
        "reset_url": reset_url,
        "logo_src": _get_logo_src(),
    }

    rendered = render_to_string(PASSWORD_RESET_TEXT, context).strip()
    lines = rendered.splitlines()

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        text_body = "\n".join(lines[1:]).lstrip("\n")
    else:
        subject = DEFAULT_RESET_SUBJECT
        text_body = rendered

    html_body = render_to_string(PASSWORD_RESET_HTML, context)

    api_key = getattr(settings, "BREVO_API_KEY", "") or os.environ.get("BREVO_API_KEY", "")

    if api_key:
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = api_key
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            sender = {
                "name": "Eventify",
                "email": settings.DEFAULT_FROM_EMAIL,
            }
            username = getattr(user, "username", "") or user_email
            to = [{"email": user_email, "name": username}]

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject=subject,
                text_content=text_body,
                html_content=html_body,
            )

            response = api_instance.send_transac_email(send_smtp_email)
            print(f"Password reset email sent successfully via Brevo API to {user_email}!")
            return response
        except ApiException as e:
            print(f"Brevo API error sending password reset email: {e}")

    # Fallback to Django Email Backend
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=f"Eventify <{settings.DEFAULT_FROM_EMAIL}>",
            to=[user_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        print(f"Password reset email sent via Django email backend to {user_email}.")
    except Exception as fallback_err:
        print("==================================================")
        print(f"[WARNING] Password reset fallback link for {user_email}:")
        print(f"Password Reset URL: {reset_url}")
        print(f"Error: {fallback_err}")
        print("==================================================")

    return None
