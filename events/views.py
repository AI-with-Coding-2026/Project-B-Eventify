from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import role_required
from authentication.models import UserRole
from .forms import EventForm
from .models import Booking, Event


@login_required
def event_detail(request, pk):
    """View details for a single event."""
    event = get_object_or_404(Event, pk=pk)

    # Calculate tickets remaining for the booking form
    tickets_sold = event.bookings.aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']
    tickets_remaining = event.max_tickets - tickets_sold

    return render(
        request,
        'events/event_detail.html',
        {
            'event': event,
            'tickets_sold': tickets_sold,
            'tickets_remaining': tickets_remaining,
        },
    )


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


@role_required(UserRole.ATTENDEE, UserRole.ADMIN)
def book_event(request, pk):
    """Book tickets for an event (attendees only)."""
    event = get_object_or_404(Event, pk=pk)

    if request.method != 'POST':
        return redirect('event_detail', pk=pk)

    # Parse quantity
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        messages.error(request, 'Ticket quantity must be at least 1.')
        return redirect('event_detail', pk=pk)

    # Calculate remaining tickets
    tickets_sold = event.bookings.aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']
    tickets_remaining = event.max_tickets - tickets_sold

    if quantity > tickets_remaining:
        if tickets_remaining == 0:
            messages.error(request, 'Sorry, this event is sold out!')
        else:
            messages.error(
                request,
                f'Only {tickets_remaining} ticket(s) remaining. '
                f'You requested {quantity}.',
            )
        return redirect('event_detail', pk=pk)

    # Create booking
    Booking.objects.create(
        event=event,
        attendee=request.user,
        quantity=quantity,
    )

    total_cost = event.ticket_price * quantity
    messages.success(
        request,
        f'Successfully booked {quantity} ticket(s) for "{event.title}"! '
        f'Total: ${total_cost:.2f}',
    )
    return redirect('event_detail', pk=pk)
