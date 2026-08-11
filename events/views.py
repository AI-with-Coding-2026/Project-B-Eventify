from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event
from .forms import EventForm


def is_organizer(user):
    """Check if the user is logged in and has the 'organizer' role."""
    return user.is_authenticated and user.role == 'organizer'


@login_required
def my_events(request):
    """
    Show a list of events created by the logged-in organizer.
    Only organizers can access this page.
    """
    if not is_organizer(request.user):
        messages.error(request, "Only organizers can access this page.")
        return redirect('home')
    
    # Get only events where the organizer is the current user
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
        # request.FILES is required for image uploads
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)  # Don't save to DB yet
            event.organizer = request.user     # Set the owner
            event.save()                       # Now save
            messages.success(request, "Event created successfully!")
            return redirect('my_events')
    else:
        form = EventForm()
    
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Create Event'})


@login_required
def edit_event(request, pk):
    """
    Allow an organizer to edit THEIR OWN event.
    The 'pk' is the event ID from the URL.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # SECURITY CHECK: Only the owner can edit
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
    Shows a confirmation page first.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # SECURITY CHECK: Only the owner can delete
    if event.organizer != request.user:
        messages.error(request, "You can only delete your own events.")
        return redirect('my_events')
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully!")
        return redirect('my_events')
    
    return render(request, 'events/delete_confirm.html', {'event': event})
    
    from django.utils import timezone

def event_list(request):
    """
    Public page showing all upcoming events.
    Anyone can see this - no login required.
    """
    events = Event.objects.filter(date__gte=timezone.now()).order_by('date')
    return render(request, 'events/event_list.html', {'events': events})