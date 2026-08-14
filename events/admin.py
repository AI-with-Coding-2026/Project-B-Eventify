from django.contrib import admin, messages
from django.template.response import TemplateResponse
from authentication.admin_site import eventify_admin_site
from .models import Event, Category, Ticket

@admin.register(Event, site=eventify_admin_site)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'date', 'price', 'category')
    actions = ['delete_selected_events']
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    @admin.action(description="Delete selected events")
    def delete_selected_events(self, request, queryset):
        # We only perform deletion if POST includes 'post' field indicating confirmation
        if request.POST.get('post'):
            deleted_count = 0
            for event in queryset:
                # Security: double check the user is admin (enforced by the site anyway)
                if request.user.is_admin:
                    event.delete()
                    deleted_count += 1
            
            if deleted_count == 1:
                self.message_user(request, "Event deleted successfully.", messages.SUCCESS)
            elif deleted_count > 1:
                self.message_user(request, "Events deleted successfully.", messages.SUCCESS)
            
            return None
            
        context = {
            **self.admin_site.each_context(request),
            'title': "Are you sure you want to delete these events?",
            'queryset': queryset,
            'action': 'delete_selected_events',
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, "admin/events/event/delete_selected_confirmation.html", context)


eventify_admin_site.register(Ticket)

# Register Category model using standard admin decorator
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}