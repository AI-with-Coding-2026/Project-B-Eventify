from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import role_required
from authentication.models import UserRole
from .forms import EventForm
from .models import Event


@role_required(UserRole.ORGANIZER, UserRole.ADMIN)
def organizer_event_list(request):
    """List events created by the logged-in organizer."""
    if request.user.is_admin:
        events = Event.objects.all()
    else:
        events = Event.objects.filter(organizer=request.user)

    return render(
        request,
        'events/event_list.html',
        {'events': events},
    )


@role_required(UserRole.ORGANIZER, UserRole.ADMIN)
def event_create(request):
    """Create a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, f'Event "{event.title}" created successfully!')
            return redirect('organizer_event_list')
    else:
        form = EventForm()

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'title': 'Create New Event',
            'action': 'Create',
        },
    )


@role_required(UserRole.ORGANIZER, UserRole.ADMIN)
def event_edit(request, pk):
    """Edit an existing event owned by the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk)

    # Authorization check: Organizer can only edit their own events
    if event.organizer != request.user and not request.user.is_admin:
        messages.error(request, 'You are not authorized to edit this event.')
        return redirect('unauthorized')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('organizer_event_list')
    else:
        # Pre-populate datetime widget format if needed
        initial_date = event.date.strftime('%Y-%m-%dT%H:%M') if event.date else None
        form = EventForm(instance=event, initial={'date': initial_date})

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'event': event,
            'title': f'Edit Event: {event.title}',
            'action': 'Update',
        },
    )


@role_required(UserRole.ORGANIZER, UserRole.ADMIN)
def event_delete(request, pk):
    """Delete an event owned by the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk)

    # Authorization check: Organizer can only delete their own events
    if event.organizer != request.user and not request.user.is_admin:
        messages.error(request, 'You are not authorized to delete this event.')
        return redirect('unauthorized')

    if request.method == 'POST':
        title = event.title
        event.delete()  # Removes record and image from storage
        messages.success(request, f'Event "{title}" deleted successfully!')
        return redirect('organizer_event_list')

    return render(
        request,
        'events/event_confirm_delete.html',
        {'event': event},
    )
