from django.contrib import admin
from authentication.admin_site import eventify_admin_site
from .models import Event, Category, Ticket

# Register Event model using custom admin site
eventify_admin_site.register(Event)
eventify_admin_site.register(Ticket)

# Register Category model using standard admin decorator
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}