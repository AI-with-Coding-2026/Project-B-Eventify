from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Event


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