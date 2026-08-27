import os
from decouple import config
from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from .models import Event, Ticket, Notification


# =========================================================
# Image Poster Controls
# =========================================================

@receiver(post_delete, sender=Event)
def delete_event_poster(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_save, sender=Event)
def delete_replaced_event_poster(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_event = Event.objects.get(pk=instance.pk)
    except Event.DoesNotExist:
        return

    old_image = old_event.image
    new_image = instance.image

    if (
        old_image
        and old_image != new_image
    ):
        old_image.delete(save=False)


# =========================================================
# Firebase Initialization (graceful — won't crash if missing)
# =========================================================

try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    cred_path = config('FIREBASE_CREDENTIALS_PATH', default='firebase-credentials.json')
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully!")
    else:
        print("Firebase credentials file not found. Push notifications disabled.")
except ImportError:
    print("firebase-admin not installed. Push notifications disabled.")
except Exception as e:
    print(f"Firebase initialization skipped: {e}")


def send_fcm_push(recipient, title, body):
    """Send a push notification via Firebase Cloud Messaging."""
    if not hasattr(recipient, 'fcm_token') or not recipient.fcm_token:
        return None

    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=recipient.fcm_token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        print(f"FCM send error for {recipient.username}: {e}")
        return None


# =========================================================
# Real-Time Booking & Cancellation Notification Signals
# =========================================================

@receiver(post_save, sender=Ticket)
def notify_organizer_on_booking(sender, instance, created, **kwargs):
    """Generates an internal notification and sends Firebase push when a ticket is booked."""
    if created:
        event = instance.event
        if event and event.organizer:
            title = "New Booking Received!"
            msg_text = f"{instance.attendee.username} has just booked {instance.quantity} ticket(s) for your event '{event.title}'."

            Notification.objects.create(
                recipient=event.organizer,
                title=title,
                message=msg_text,
                event=event
            )

            send_fcm_push(event.organizer, title, msg_text)


@receiver(post_delete, sender=Ticket)
def notify_organizer_on_cancellation(sender, instance, **kwargs):
    """Generates an internal notification and sends Firebase push when a booking is cancelled."""
    event = instance.event
    if event and event.organizer:
        title = "Booking Cancelled"
        msg_text = f"{instance.attendee.username} cancelled their booking of {instance.quantity} ticket(s) for your event '{event.title}'."

        Notification.objects.create(
            recipient=event.organizer,
            title=title,
            message=msg_text,
            event=event
        )

        send_fcm_push(event.organizer, title, msg_text)