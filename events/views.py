import threading
from urllib.parse import urlparse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from authentication.decorators import (
    admin_required,
    attendee_required,
    organizer_required,
    role_required,
)
from authentication.models import UserRole
from .emails import send_booking_confirmation_email
from .forms import BookingForm, CategoryForm, EventForm, TicketForm
from .models import Category, Event, EventBooking, Ticket


def _user_can_manage_event(user, event):
    if user.is_admin:
        return True
    return (
        user.role == UserRole.ORGANIZER
        and event.organizer_id == user.id
    )


def _user_has_booked_event(user, event):
    return Ticket.objects.filter(
        attendee=user,
        event=event,
    ).exists() or EventBooking.objects.filter(
        user=user,
        event=event,
    ).exists()


# Map URL path prefixes to human-readable back-button labels.
_BACK_LABEL_MAP = [
    ('/admin/', 'Back to Admin Dashboard'),
    ('/dashboard/organizer/', 'Back to Organizer Dashboard'),
    ('/dashboard/attendee/bookings/', 'Back to My Bookings'),
    ('/dashboard/attendee/', 'Back to Attendee Dashboard'),
    ('/events/organizer/', 'Back to Organizer Events'),
    ('/my-bookings/', 'Back to My Bookings'),
    ('/bookings/', 'Back to My Bookings'),
    ('/events/mine/', 'Back to My Events'),
    ('/events/my-tickets/', 'Back to My Tickets'),
    ('/events/', 'Back to Events'),
]

def get_user_bookings(user_id):
    """
    Fetch all bookings for a given user ID, combining current Ticket
    records and legacy EventBooking records into one list.
    """
    tickets = Ticket.objects.filter(
        attendee_id=user_id
    ).select_related('event').order_by('-booked_at')

    legacy_bookings = EventBooking.objects.filter(
        user_id=user_id
    ).select_related('event').order_by('-booked_at')

    bookings = []

    for ticket in tickets:
        bookings.append({
            'event': ticket.event,
            'quantity': ticket.quantity,
            'booked_at': ticket.booked_at,
            'source': 'ticket',
        })

    for booking in legacy_bookings:
        bookings.append({
            'event': booking.event,
            'quantity': 1,
           'booked_at': booking.booked_at,
            'source': 'legacy',
        })

    bookings.sort(key=lambda b: b['booked_at'], reverse=True)

    return bookings

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

    today = timezone.now().date()
    past_events = events.filter(date__date__lt=today).order_by('-date')
    events = events.filter(date__date__gte=today)
    selling_fast_threshold = 10  # tweak this number as needed

    paginator = Paginator(events, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': Event.get_all_category_choices(),
        'search_query': search_query,
        'selected_category': selected_category,
        'max_price': max_price,
        'start_date': start_date,
        'end_date': end_date,
        'filter_query_string': filter_query_string,
        'past_events': past_events,
        'selling_fast_threshold': selling_fast_threshold,
    }
    return render(request, 'events/event_list.html', context)

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    user_has_booked = False

    if user.is_authenticated:
        user_has_booked = _user_has_booked_event(user, event)


    is_past_event = event.date < timezone.now()

    context = {
        'event': event,
        'can_manage': user.is_authenticated and _user_can_manage_event(user, event),
        'can_book': (
            user.is_authenticated
            and user.role == UserRole.ATTENDEE
            and not user_has_booked
            and not event.is_sold_out
            and not event.is_expired
        ),
        'user_has_booked': user_has_booked,
        'is_past_event': event.is_expired,
    }
    return render(request, 'events/event_detail.html', context)


@role_required(UserRole.ATTENDEE)
def book_event(request, pk):
    """Keep the legacy endpoint from bypassing the ticket-capacity flow."""
    return redirect('book_ticket', pk=pk)


@attendee_required
def book_ticket(request, pk):
    """Book tickets without allowing a request to exceed event capacity."""
    event = get_object_or_404(Event, pk=pk)

    if event.is_expired:
        messages.error(request, 'Booking is not available because this event has ended.')
        return redirect('event_detail', pk=pk)

    if _user_has_booked_event(request.user, event):
        messages.info(request, 'You have already booked this event.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 1:
            messages.error(request, 'Choose at least one ticket.')
        else:
            with transaction.atomic():
                event = Event.objects.select_for_update().get(pk=pk)
                tickets_sold = Ticket.objects.filter(event=event).aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                tickets_sold += event.bookings.count()
                remaining = event.max_tickets - tickets_sold

                if quantity > remaining:
                    if remaining <= 0:
                        messages.error(request, 'This event is sold out.')
                    else:
                        messages.error(
                            request,
                            f'Only {remaining} ticket(s) remain for this event.',
                        )
                elif _user_has_booked_event(request.user, event):
                    messages.info(request, 'You have already booked this event.')
                else:
                    ticket = Ticket.objects.create(
                        event=event,
                        attendee=request.user,
                        quantity=quantity,
                    )
                    
                    # --------------------------------------------------
                    # التعديل هنا: تشغيل الإرسال في الخلفية دون تعليق السيرفر
                    # --------------------------------------------------
                    threading.Thread(
                        target=send_booking_confirmation_email,
                        args=(ticket,)
                    ).start()

                    messages.success(
                        request,
                        f'Ticket booked for "{event.title}". Confirmation email is on its way.',
                    )

                    return redirect('my_bookings')

    return render(
        request,
        'events/book_ticket.html',
        {'event': event},
    )


@attendee_required
def my_tickets(request):
    """Redirect legacy my_tickets endpoint to unified my_bookings page."""
    return redirect('my_bookings')


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
def event_create(request):
    """Create an event and assign the logged-in organizer as owner."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully.')
            if request.user.is_admin:
                return redirect('admin_dashboard')
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
            if request.user.is_admin:
                return redirect('admin_dashboard')
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
        if request.user.is_admin:
            return redirect('admin_dashboard')
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

            return redirect('admin_dashboard')

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

            if request.user.is_admin:
                return redirect("admin_dashboard")

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