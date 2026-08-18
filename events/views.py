from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse

from authentication.decorators import (
    admin_required,
    attendee_required,
    organizer_required,
    role_required,
)
from authentication.models import UserRole
from .forms import BookingForm, CategoryForm, EventForm, TicketForm
from .models import Category, Event, EventBooking, Ticket
from django.db.models import Count

@organizer_required
def organizer_performance(request):
    """Performance dashboard for the logged-in organizer."""

    events = (
        Event.objects
        .filter(organizer=request.user)
        .annotate(tickets_sold=Count('bookings', distinct=True))
        .order_by('-date')
    )

    total_tickets_sold = 0
    total_revenue = 0

    for event in events:
        event.tickets_remaining_for_performance = max(
            event.max_tickets - event.tickets_sold,
            0,
        )

        event.revenue_for_performance = (
            event.price * event.tickets_sold
        )

        total_tickets_sold += event.tickets_sold
        total_revenue += event.revenue_for_performance

    return render(
        request,
        'events/organizer_performance.html',
        {
            'events': events,
            'total_tickets_sold': total_tickets_sold,
            'total_revenue': total_revenue,
        },
    )


def _user_can_manage_event(user, event):
    if user.is_admin:
        return True
    return (
        user.role == UserRole.ORGANIZER
        and event.organizer_id == user.id
    )


# Map URL path prefixes to human-readable back-button labels.
_BACK_LABEL_MAP = [
    ('/admin/', 'Back to Admin Dashboard'),
    ('/dashboard/organizer/', 'Back to Organizer Dashboard'),
    ('/dashboard/attendee/', 'Back to Attendee Dashboard'),
    ('/events/mine/', 'Back to My Events'),
    ('/events/', 'Back to Events'),
]


def _resolve_back_navigation(request):
    """Return (back_url, back_label) from the HTTP Referer header.

    Falls back to the event list if the referer is missing, external,
    or points at the current page itself.
    """
    from django.urls import reverse

    default_url = reverse('event_list')
    default_label = 'Back to Events'

    referer = request.META.get('HTTP_REFERER', '')
    if not referer:
        return default_url, default_label

    # Reject external / unsafe URLs.
    if not url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return default_url, default_label

    parsed_path = urlparse(referer).path

    # Don't link back to the same detail page.
    if parsed_path == request.path:
        return default_url, default_label

    # Pick the most specific matching label.
    for prefix, label in _BACK_LABEL_MAP:
        if parsed_path.startswith(prefix):
            return referer, label

    # Home page or any other internal page – still honour the referer.
    return referer, 'Back'


def event_list(request):
    events = Event.objects.all().order_by('date')

    search_query = request.GET.get('search', '')
    selected_category = request.GET.get('category', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    max_price = request.GET.get('max_price', '')

    if search_query:
        events = events.filter(title__icontains=search_query)

    if selected_category:
        events = events.filter(category=selected_category)

    if max_price:
        events = events.filter(price__lte=max_price)

    if start_date and end_date:
        events = events.filter(date__date__range=(start_date, end_date))
    else:
        if start_date:
            events = events.filter(date__date__gte=start_date)
        if end_date:
            events = events.filter(date__date__lte=end_date)

    paginator = Paginator(events, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': Event.CATEGORY_CHOICES,
        'search_query': search_query,
        'selected_category': selected_category,
        'max_price': max_price,
        'start_date': start_date,
        'end_date': end_date,
        'filter_query_string': filter_query_string,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    user_has_booked = False

    if user.is_authenticated:
        user_has_booked = Ticket.objects.filter(
            attendee=user,
            event=event,
        ).exists()

    back_url, back_label = _resolve_back_navigation(request)

    context = {
        'event': event,
        'can_manage': user.is_authenticated and _user_can_manage_event(user, event),
        'can_book': (
            user.is_authenticated
            and user.role == UserRole.ATTENDEE
            and not user_has_booked
            and not event.is_sold_out
        ),
        'user_has_booked': user_has_booked,
        'back_url': back_url,
        'back_label': back_label,
    }
    return render(request, 'events/event_detail.html', context)


@role_required(UserRole.ATTENDEE)
def book_event(request, pk):
    if request.method != 'POST':
        return redirect('event_detail', pk=pk)

    event = get_object_or_404(Event, pk=pk)

    if EventBooking.objects.filter(user=request.user, event=event).exists():
        messages.info(request, f'You have already booked "{event.title}".')
        return redirect('event_detail', pk=pk)

    if event.is_sold_out:
        messages.error(request, 'This event is fully booked.')
        return redirect('event_detail', pk=pk)

    EventBooking.objects.create(user=request.user, event=event)
    messages.success(request, f'Successfully booked "{event.title}".')
    return redirect('event_detail', pk=pk)


@attendee_required
def book_ticket(request, pk):
    """Allow attendees to book a ticket for an event."""
    event = get_object_or_404(Event, pk=pk)

    # Check if user already has a ticket for this event
    if Ticket.objects.filter(attendee=request.user, event=event).exists():
        messages.info(request, f'You have already booked a ticket for "{event.title}".')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1

        Ticket.objects.create(
            event=event,
            attendee=request.user,
            quantity=quantity,
        )
        messages.success(
            request,
            f'Ticket booked for "{event.title}".',
        )
        return redirect('my_tickets')

    return render(
        request,
        'events/book_ticket.html',
        {'event': event},
    )


@attendee_required
def my_tickets(request):
    """Show tickets booked by the logged-in attendee."""
    tickets = (
        Ticket.objects.filter(attendee=request.user)
        .select_related('event')
        .order_by('-booked_at')
    )
    return render(
        request,
        'events/my_tickets.html',
        {'tickets': tickets},
    )

@organizer_required
def organizer_event_list(request):
    """Show only events owned by the logged-in organizer."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')
    return render(
        request,
        'events/organizer_event_list.html',
        {'events': events},
    )


@organizer_required
def organizer_performance(request):
    """Show ticket sales and revenue for the logged-in organizer's events."""
    events = (
        Event.objects
        .filter(organizer=request.user)
        .prefetch_related('tickets')
    )

    total_tickets_sold = 0
    total_revenue = 0

    for event in events:
        event.tickets_sold = sum(
            ticket.quantity
            for ticket in event.tickets.all()
        )

        event.performance_tickets_remaining = max(
            event.max_tickets - event.tickets_sold,
            0,
        )

        event.revenue = event.price * event.tickets_sold

        total_tickets_sold += event.tickets_sold
        total_revenue += event.revenue

    return render(
        request,
        'events/organizer_performance.html',
        {
            'events': events,
            'total_tickets_sold': total_tickets_sold,
            'total_revenue': total_revenue,
        },
    )


@organizer_required
def event_create(request):
    """Create an event and assign the logged-in organizer as owner."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully.')
            return redirect('organizer_event_list')
    else:
        form = EventForm()

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'page_title': 'Create Event',
            'submit_label': 'Create Event',
        },
    )


@organizer_required
def event_edit(request, pk):
    """Edit an event only if it belongs to the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            return redirect('organizer_event_list')
    else:
        form = EventForm(instance=event)

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'event': event,
            'page_title': 'Edit Event',
            'submit_label': 'Update Event',
        },
    )


@organizer_required
def event_delete(request, pk):
    """Delete an event only if it belongs to the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('organizer_event_list')

    return render(
        request,
        'events/event_confirm_delete.html',
        {'event': event},
    )


@admin_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'events/category_list.html', {'categories': categories})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.',
            )

            return redirect('category_create')

    else:
        form = CategoryForm()

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            'page_title': 'Create Category',
            'submit_label': 'Save Category',
        },
    )


@admin_required
def category_update(request, pk):
    """Allow admins to edit an existing category name/description."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category updated successfully.'
            )

            return redirect('category_update', pk=category.pk)

    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            'category': category,
            'page_title': 'Edit Category',
            'submit_label': 'Update Category',
        },
    )


@admin_required
def category_delete(request, pk):
    """Allow admins to delete an existing category after confirmation."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()
        messages.success(
            request,
            'Category deleted successfully.'
        )
        return redirect('category_list')

    return render(
        request,
        'events/category_confirm_delete.html',
        {'category': category},
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

            return redirect("my_events")

    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "page_title": "Create Event",
            "submit_label": "Create Event",
        },
    )


@role_required(UserRole.ORGANIZER)
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not _user_can_manage_event(request.user, event):
        raise PermissionDenied

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
                "event_detail",
                pk=event.pk,
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
            "submit_label": "Update Event",
        },
    )


@role_required(UserRole.ORGANIZER)
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not _user_can_manage_event(request.user, event):
        raise PermissionDenied

    if request.method == "POST":
        event.delete()

        messages.success(
            request,
            "Event deleted successfully.",
        )

        if request.user.is_admin:
            return redirect(request.POST.get("next") or "admin_dashboard")

        return redirect("my_events")

    return render(
        request,
        "events/event_confirm_delete.html",
        {
            "event": event,
        },
    )


@admin_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == "POST":
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket updated successfully.")
            return redirect("admin_dashboard")
    else:
        form = TicketForm(instance=ticket)

    return render(
        request,
        "events/ticket_form.html",
        {
            "form": form,
            "ticket": ticket,
            "page_title": "Edit Ticket",
            "submit_label": "Update Ticket",
        },
    )


@admin_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == "POST":
        ticket.delete()
        messages.success(request, "Ticket deleted successfully.")
        return redirect("admin_dashboard")

    return render(
        request,
        "events/ticket_confirm_delete.html",
        {
            "ticket": ticket,
        },
    )


@admin_required
def booking_edit(request, pk):
    booking = get_object_or_404(EventBooking, pk=pk)

    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking updated successfully.")
            return redirect("admin_dashboard")
    else:
        form = BookingForm(instance=booking)

    return render(
        request,
        "events/booking_form.html",
        {
            "form": form,
            "booking": booking,
            "page_title": "Edit Booking",
            "submit_label": "Update Booking",
        },
    )


@admin_required
def booking_delete(request, pk):
    booking = get_object_or_404(EventBooking, pk=pk)

    if request.method == "POST":
        booking.delete()
        messages.success(request, "Booking deleted successfully.")
        return redirect("admin_dashboard")

    return render(
        request,
        "events/booking_confirm_delete.html",
        {
            "booking": booking,
        },
    )
