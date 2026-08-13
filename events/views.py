from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Event
from .forms import EventForm


def is_organizer(user):
    """Check if the user is logged in and has the 'organizer' role."""
    return user.is_authenticated and user.role == 'organizer'


def event_list(request):
    """
    Public page showing all upcoming events.
    Anyone can see this - no login required.
    """
    events = Event.objects.filter(date__gte=timezone.now()).order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


def event_detail(request, pk):
    """
    Public detail page for a single event.
    Anyone can view: attendees, organizers, admins, or logged-out users.
    """
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'events/event_detail.html', {'event': event})


@login_required
def my_events(request):
    """
    Show a list of events created by the logged-in organizer.
    Only organizers can access this page.
    """
    if not is_organizer(request.user):
        messages.error(request, "Only organizers can access this page.")
        return redirect('home')
    
    events = Event.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'events/my_events.html', {'events': events})


@login_required
def create_event(request):
    """
    Allow an organizer to create a new event.
    Automatically sets the current user as the organizer.
    """
    if not is_organizer(request.user):
        messages.error(request, "Only organizers can create events.")
        return redirect('home')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "Event created successfully!")
            return redirect('my_events')
    else:
        form = EventForm()
    
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Create Event'})


@login_required
def edit_event(request, pk):
    """
    Allow an organizer to edit THEIR OWN event.
    """
    event = get_object_or_404(Event, pk=pk)
    
    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('my_events')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully!")
            return redirect('my_events')
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'title': 'Edit Event',
        'event': event
    })


@login_required
def delete_event(request, pk):
    """
    Allow an organizer to delete THEIR OWN event.
    Allow an admin to delete ANY event.
    """
    event = get_object_or_404(Event, pk=pk)
    
    is_owner = event.organizer == request.user
    is_admin = request.user.role == 'admin'
    
    if not (is_owner or is_admin):
        messages.error(request, "You can only delete your own events.")
        return redirect('my_events')
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully!")
        if is_admin and not is_owner:
            return redirect('event_list')
        return redirect('my_events')
    
    return render(request, 'events/delete_confirm.html', {'event': event})