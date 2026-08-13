from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404

from authentication.decorators import admin_required, role_required
from authentication.models import UserRole
from .forms import CategoryForm, EventForm
from .models import Event




def event_list(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.'
            )

            return redirect('category_create')

    else:
        form = CategoryForm()

    return render(
        request,
        'events/category_form.html',
        {'form': form}
    )

@role_required(UserRole.ORGANIZER)
def my_events(request):
    events = Event.objects.filter(
        organizer=request.user
    )

    return render(
        request,
        "events/my_events.html",
        {
            "events": events,
        },
    )


@role_required(UserRole.ORGANIZER)
def create_event(request):
    if request.method == "POST":
        form = EventForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            messages.success(
                request,
                "Event created successfully.",
            )

            return redirect(
                "my_events"
            )

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


@role_required(UserRole.ORGANIZER)
def edit_event(request, pk):
    event = get_object_or_404(
        Event,
        pk=pk,
        organizer=request.user,
    )

    if request.method == "POST":
        form = EventForm(
            request.POST,
            request.FILES,
            instance=event,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Event updated successfully.",
            )

            return redirect(
                "my_events"
            )

    else:
        form = EventForm(
            instance=event
        )

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "event": event,
            "page_title": "Edit Event",
        },
    )


@role_required(UserRole.ORGANIZER)
def delete_event(request, pk):
    event = get_object_or_404(
        Event,
        pk=pk,
        organizer=request.user,
    )

    if request.method == "POST":
        event.delete()

        messages.success(
            request,
            "Event deleted successfully.",
        )

        return redirect(
            "my_events"
        )

    return render(
        request,
        "events/event_confirm_delete.html",
        {
            "event": event,
        },
    )