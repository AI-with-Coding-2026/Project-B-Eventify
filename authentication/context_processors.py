from events.models import Event, EventPublishStatus


def dashboard_link(request):
    """Expose the role-appropriate dashboard URL name to all templates."""
    context = {
        'user_dashboard_url': 'home',
        'pending_event_count': 0,
        'can_publish_events': False,
    }

    if not request.user.is_authenticated:
        return context

    context['can_publish_events'] = request.user.is_admin or request.user.is_organizer

    if request.user.is_admin:
        context['user_dashboard_url'] = 'admin_dashboard'
        context['pending_event_count'] = Event.objects.filter(
            publish_status=EventPublishStatus.PENDING,
        ).count()
        return context

    if request.user.is_organizer:
        context['user_dashboard_url'] = 'organizer_dashboard'
        return context

    context['user_dashboard_url'] = 'attendee_dashboard'
    return context
