import os
from pathlib import Path
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from django.conf import settings
from django.template.loader import render_to_string


VERIFICATION_TEXT = "authentication/verification_email.txt"
VERIFICATION_HTML = "authentication/verification_email.html"
DEFAULT_SUBJECT = "Verify your Eventify email address"
LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'eventify_no_background.png'


def _get_logo_src():
    if LOGO_PATH.exists():
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        return f"{site_url}/static/images/eventify_no_background.png"
    return ""


def send_verification_email(user, verification_url):
    """
    Send an email-verification message for a newly created account.
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

    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        print("==================================================")
        print("⚠️ BREVO_API_KEY not set. Verification link:")
        print(f"🔗 {verification_url}")
        print("==================================================")
        return None

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

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Verification email sent successfully via Brevo API!")
        return response
    except ApiException as e:
        print(f"Brevo API error sending verification email: {e}")
        print(f"Fallback verification link: {verification_url}")
        raise e
