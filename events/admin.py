from authentication.admin_site import eventify_admin_site
from .models import Event

eventify_admin_site.register(Event)