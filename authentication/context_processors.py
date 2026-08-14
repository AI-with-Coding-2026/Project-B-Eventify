def dashboard_link(request):
    """Expose the role-appropriate dashboard URL name to all templates."""
    if not request.user.is_authenticated:
        return {'user_dashboard_url': 'home'}

    if request.user.is_admin:
        return {'user_dashboard_url': 'admin_dashboard'}

    if request.user.is_organizer:
        return {'user_dashboard_url': 'organizer_dashboard'}

    return {'user_dashboard_url': 'attendee_dashboard'}
