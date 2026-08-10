import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Event

@receiver(post_delete, sender=Event)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem when corresponding `Event` object is deleted.
    """
    if instance.poster_image:
        if os.path.isfile(instance.poster_image.path):
            os.remove(instance.poster_image.path)

@receiver(pre_save, sender=Event)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem when corresponding `Event` object is updated with new file.
    """
    if not instance.pk:
        return False

    try:
        old_file = Event.objects.get(pk=instance.pk).poster_image
    except Event.DoesNotExist:
        return False

    new_file = instance.poster_image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)
