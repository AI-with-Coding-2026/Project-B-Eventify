from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EventForm
from .models import Event


def organizer_required(user):
    return user.is_authenticated and user.role == "organizer"


@login_required
def event_list(request):
    if not organizer_required(request.user):
        raise PermissionDenied

    events = Event.objects.filter(
        organizer=request.user
    ).order_by("-date")

    return render(
        request,
        "events/event_list.html",
        {"events": events},
    )


@login_required
def event_create(request):
    if not organizer_required(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)

        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            return redirect("event_list")
    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "page_title": "Create Event",
        },
    )


@login_required
def event_edit(request, pk):
    if not organizer_required(request.user):
        raise PermissionDenied

    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user:
        raise PermissionDenied

    if request.method == "POST":
        old_poster = event.poster

        form = EventForm(
            request.POST,
            request.FILES,
            instance=event,
        )

        if form.is_valid():
            updated_event = form.save()

            if (
                old_poster
                and request.FILES.get("poster")
                and old_poster.name != updated_event.poster.name
            ):
                old_poster.delete(save=False)

            return redirect("event_list")
    else:
        form = EventForm(instance=event)

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "page_title": "Edit Event",
        },
    )


@login_required
def event_delete(request, pk):
    if not organizer_required(request.user):
        raise PermissionDenied

    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user:
        raise PermissionDenied

    if request.method == "POST":
        if event.poster:
            event.poster.delete(save=False)

        event.delete()

        return redirect("event_list")

    return render(
        request,
        "events/event_confirm_delete.html",
        {"event": event},
    )