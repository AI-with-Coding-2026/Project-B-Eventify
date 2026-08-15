from django.contrib import admin
from django.utils.html import format_html
from authentication.admin_site import eventify_admin_site
from .models import Event, Category, EventBooking, Ticket


def render_actions_menu(obj):
    edit_url = f'{obj.pk}/change/'
    delete_url = f'{obj.pk}/delete/'
    return format_html(
        '<div style="text-align: right; width: 100%;">'
        '  <div style="display:inline-block;position:relative;">'
        '    <button type="button" onclick="'
        "      var b=this.getBoundingClientRect();"
        "      var m=this.nextElementSibling;"
        "      document.querySelectorAll('.evt-dropdown').forEach(function(d){{if(d!==m)d.style.display='none'}});"
        "      if(m.style.display==='block'){{m.style.display='none';return}}"
        "      m.style.top=b.bottom+'px';"
        "      m.style.left=(b.right-120)+'px';"
        "      m.style.display='block';"
        "      event.stopPropagation();"
        '"'
        '    style="background:none;border:none;cursor:pointer;font-size:20px;'
        '    line-height:1;padding:4px 8px;color:inherit;">&#8942;</button>'
        '    <div class="evt-dropdown" style="display:none;position:fixed;'
        '    background:#1a1a2e;border:1px solid #444;border-radius:4px;min-width:120px;'
        '    z-index:10000;box-shadow:0 2px 8px rgba(0,0,0,.3);text-align:left;">'
        '      <a href="{edit_url}" style="display:block;padding:8px 16px;color:#79aec8;'
        '      text-decoration:none;white-space:nowrap;font-size:13px;"'
        '      onmouseover="this.style.background=\'#264b5d\'"'
        '      onmouseout="this.style.background=\'none\'">Edit</a>'
        '      <a href="{delete_url}" style="display:block;padding:8px 16px;color:#e74c3c;'
        '      text-decoration:none;white-space:nowrap;font-size:13px;"'
        '      onmouseover="this.style.background=\'#4a1a1a\'"'
        '      onmouseout="this.style.background=\'none\'">Delete</a>'
        '    </div>'
        '  </div>'
        '</div>'
        '<script>'
        "document.addEventListener('click',function(){{document.querySelectorAll('.evt-dropdown')"
        ".forEach(function(d){{d.style.display='none'}})}});"
        '</script>',
        edit_url=edit_url,
        delete_url=delete_url,
    )


class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'date', 'price', 'category', 'actions_menu')
    list_filter = ('category', 'date')
    search_fields = ('title', 'organizer__username', 'location')

    @admin.display(description='')
    def actions_menu(self, obj):
        return render_actions_menu(obj)


eventify_admin_site.register(Event, EventAdmin)


class TicketAdmin(admin.ModelAdmin):
    list_display = ('attendee', 'event', 'quantity', 'booked_at', 'actions_menu')
    list_filter = ('booked_at',)
    search_fields = ('attendee__username', 'event__title')
    ordering = ('-booked_at',)

    @admin.display(description='')
    def actions_menu(self, obj):
        return render_actions_menu(obj)


eventify_admin_site.register(Ticket, TicketAdmin)


class EventBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'booked_at', 'actions_menu')
    list_filter = ('booked_at',)
    search_fields = ('user__username', 'event__title')
    ordering = ('-booked_at',)

    @admin.display(description='')
    def actions_menu(self, obj):
        return render_actions_menu(obj)


eventify_admin_site.register(EventBooking, EventBookingAdmin)

# Register Category model using standard admin decorator
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}