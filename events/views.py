from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking

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


@login_required
def organizer_dashboard(request):
    if not organizer_required(request.user):
        raise PermissionDenied

    events = (
        Event.objects.filter(organizer=request.user)
        .annotate(
            tickets_sold=Sum(
                "bookings__quantity",
                filter=Q(
                    bookings__status=Booking.Status.CONFIRMED
                ),
            )
        )
        .order_by("-date")
    )

    event_stats = []

    total_tickets_sold = 0
    total_tickets_remaining = 0
    total_revenue = Decimal("0.00")

    for event in events:
        tickets_sold = event.tickets_sold or 0

        tickets_remaining = max(
            event.max_tickets - tickets_sold,
            0,
        )

        revenue = event.ticket_price * tickets_sold

        total_tickets_sold += tickets_sold
        total_tickets_remaining += tickets_remaining
        total_revenue += revenue

        event_stats.append(
            {
                "event": event,
                "tickets_sold": tickets_sold,
                "tickets_remaining": tickets_remaining,
                "revenue": revenue,
            }
        )

    context = {
        "event_stats": event_stats,
        "total_events": len(event_stats),
        "total_tickets_sold": total_tickets_sold,
        "total_tickets_remaining": total_tickets_remaining,
        "total_revenue": total_revenue,
    }

    return render(
        request,
        "events/organizer_dashboard.html",
        context,
    )


@login_required
def attendee_event_list(request):
    if not request.user.is_attendee:
        raise PermissionDenied

    # Task 3 & Task 2: Extract search, location, and sort inputs from request
    search_query = request.GET.get("q", "").strip()
    location_query = request.GET.get("location", "").strip()
    sort_order = request.GET.get("sort", "asc")

    # Base QuerySet: Filter out past events
    events = Event.objects.filter(date__gte=timezone.now())

    # Text Search Filter
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    # Location Filter (Venue/City search)
    if location_query:
        events = events.filter(location__icontains=location_query)

    # Chronological Sorting
    if sort_order == "desc":
        events = events.order_by("-date")  # Furthest out first
    else:
        events = events.order_by("date")   # Soonest date first

    event_cards = []

    for event in events:
        tickets_sold = (
            event.bookings.filter(
                status=Booking.Status.CONFIRMED
            )
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        tickets_remaining = max(
            event.max_tickets - tickets_sold,
            0,
        )

        event_cards.append(
            {
                "event": event,
                "tickets_sold": tickets_sold,
                "tickets_remaining": tickets_remaining,
            }
        )

    return render(
        request,
        "events/attendee_event_list.html",
        {
            "event_cards": event_cards,
            "search_query": search_query,
            "location_query": location_query,
            "current_sort": sort_order,
        },
    )