from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EventForm
from .models import Event


def organizer_required(view_func):
    """
    Allow access only to authenticated organizers.
    """

    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_organizer:
            messages.error(
                request,
                'Only organizers can manage events.'
            )
            return redirect('unauthorized')

        return view_func(request, *args, **kwargs)

    return wrapper


@organizer_required
def organizer_event_list(request):
    """
    Display only the events created by the logged-in organizer.
    """

    events = Event.objects.filter(
        organizer=request.user
    ).order_by('-date')

    return render(
        request,
        'EventMan/organizer_event_list.html',
        {'events': events}
    )


@organizer_required
def create_event(request):
    """
    Create a new event and automatically assign the
    logged-in organizer as its owner.
    """

    if request.method == 'POST':
        form = EventForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            event = form.save(commit=False)

            # The organizer comes from the logged-in user.
            # It is NOT supplied by the form.
            event.organizer = request.user

            event.save()

            messages.success(
                request,
                'Event created successfully.'
            )

            return redirect('organizer_event_list')

    else:
        form = EventForm()

    return render(
        request,
        'EventMan/event_form.html',
        {
            'form': form,
            'page_title': 'Create Event',
        }
    )


@organizer_required
def edit_event(request, event_id):
    """
    Edit an event only if it belongs to the logged-in organizer.
    """

    event = get_object_or_404(
        Event,
        id=event_id,
        organizer=request.user
    )

    old_poster = event.poster

    if request.method == 'POST':
        form = EventForm(
            request.POST,
            request.FILES,
            instance=event
        )

        if form.is_valid():
            updated_event = form.save()

            # If a new poster was uploaded, remove the old poster.
            if (
                old_poster
                and old_poster.name
                and 'poster' in request.FILES
            ):
                old_poster.delete(save=False)

            messages.success(
                request,
                'Event updated successfully.'
            )

            return redirect('organizer_event_list')

    else:
        form = EventForm(instance=event)

    return render(
        request,
        'EventMan/event_form.html',
        {
            'form': form,
            'event': event,
            'page_title': 'Edit Event',
        }
    )


@organizer_required
def delete_event(request, event_id):
    """
    Delete an event only if it belongs to the logged-in organizer.
    The stored poster image is also removed.
    """

    event = get_object_or_404(
        Event,
        id=event_id,
        organizer=request.user
    )

    if request.method == 'POST':
        poster = event.poster

        event.delete()

        # Remove the stored poster file.
        if poster and poster.name:
            poster.delete(save=False)

        messages.success(
            request,
            'Event deleted successfully.'
        )

        return redirect('organizer_event_list')

    return render(
        request,
        'EventMan/event_confirm_delete.html',
        {'event': event}
    )