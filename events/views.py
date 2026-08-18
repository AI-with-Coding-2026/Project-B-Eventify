from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import organizer_required
from .forms import EventForm
from .models import Event


@organizer_required
def event_list_view(request):
    events = Event.objects.filter(organizer=request.user)

    return render(
        request,
        "events/event_list.html",
        {"events": events},
    )


@organizer_required
def event_create_view(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)

        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            messages.success(request, "Event created successfully.")

            return redirect("events:event_list")
    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {"form": form, "is_edit": False},
    )


@organizer_required
def event_update_view(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    old_poster = event.poster

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)

        if form.is_valid():
            updated_event = form.save()

            # A new poster was uploaded: remove the old file from storage.
            if old_poster and old_poster != updated_event.poster:
                old_poster.delete(save=False)

            messages.success(request, "Event updated successfully.")

            return redirect("events:event_list")
    else:
        form = EventForm(instance=event)

    return render(
        request,
        "events/event_form.html",
        {"form": form, "is_edit": True, "event": event},
    )


@organizer_required
def event_delete_view(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == "POST":
        if event.poster:
            event.poster.delete(save=False)

        event.delete()

        messages.success(request, "Event deleted successfully.")

        return redirect("events:event_list")

    return render(
        request,
        "events/event_confirm_delete.html",
        {"event": event},
    )
