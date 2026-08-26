from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from events.emails import (
    _brevo_session,
    _get_brevo_api_key,
    send_booking_cancellation_email,
)
from events.models import Event, Ticket


class Command(BaseCommand):
    help = (
        "Send a real booking-cancellation email through Brevo without "
        "deleting a ticket. Use this to check whether the email is sent "
        "and delivered."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticket-id",
            type=int,
            help="Existing ticket ID to use for event/attendee details.",
        )
        parser.add_argument(
            "--to",
            help="Override recipient email. Defaults to the ticket attendee.",
        )

    def handle(self, *args, **options):
        api_key = _get_brevo_api_key()
        if not api_key:
            raise CommandError(
                "BREVO_API_KEY is missing. Set it in your .env file."
            )

        self.stdout.write("Checking HTTPS connection to api.brevo.com...")
        try:
            probe = _brevo_session().get(
                "https://api.brevo.com/v3/account",
                headers={
                    "api-key": api_key,
                    "Accept": "application/json",
                },
                timeout=30,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Brevo API reachable (HTTP {probe.status_code})."
                )
            )
        except Exception as exc:
            raise CommandError(
                f"Cannot reach Brevo API. SSL/network error: {exc}"
            ) from exc

        ticket = self._build_ticket(
            ticket_id=options.get("ticket_id"),
            to_email=options.get("to"),
        )
        recipient = ticket.attendee.email

        self.stdout.write(
            f"Sending cancellation email to {recipient} "
            f"for event '{ticket.event.title}'..."
        )

        try:
            response = send_booking_cancellation_email(ticket)
        except Exception as exc:
            raise CommandError(f"Cancellation email failed: {exc}") from exc

        message_id = ""
        if isinstance(response, dict):
            message_id = response.get("messageId") or response.get("message_id") or ""

        self.stdout.write(self.style.SUCCESS("Brevo accepted the email."))
        if message_id:
            self.stdout.write(f"Brevo message ID: {message_id}")
        self.stdout.write(
            f"Check the inbox (and spam folder) for {recipient}. "
            "Subject: Your Eventify Booking Cancellation Confirmation"
        )

    def _build_ticket(self, ticket_id, to_email):
        if ticket_id:
            ticket = Ticket.objects.select_related("event", "attendee").filter(
                pk=ticket_id
            ).first()
            if ticket is None:
                raise CommandError(f"Ticket {ticket_id} was not found.")
        else:
            ticket = (
                Ticket.objects.select_related("event", "attendee")
                .order_by("-booked_at")
                .first()
            )

        if ticket is None:
            event = Event.objects.first()
            if event is None:
                raise CommandError(
                    "No tickets or events exist. Create an event/booking first."
                )
            attendee = SimpleNamespace(
                username="Test Attendee",
                email=to_email or "",
            )
            if not attendee.email:
                raise CommandError(
                    "No tickets found. Pass --to your@email.com to send a sample."
                )
            return SimpleNamespace(
                event=event,
                attendee=attendee,
                quantity=1,
                booked_at=timezone.now(),
            )

        if to_email:
            return SimpleNamespace(
                event=ticket.event,
                attendee=SimpleNamespace(
                    username=ticket.attendee.username,
                    email=to_email,
                ),
                quantity=ticket.quantity,
                booked_at=ticket.booked_at,
            )

        if not (ticket.attendee.email or "").strip():
            raise CommandError(
                "That attendee has no email. Pass --to your@email.com."
            )

        return ticket
