import json
import threading
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.decorators import api_view
from rest_framework.response import Response

from authentication.decorators import (
    admin_required,
    attendee_required,
    organizer_required,
    role_required,
    organizer_or_admin_required,
    approved_organizer_required,
)
from authentication.models import UserRole
from .emails import send_booking_confirmation_email
from .forms import BookingForm, CategoryForm, EventForm, TicketForm
from .models import Category, Event, EventBooking, EventPublishStatus, Notification, Ticket
from .serializers import EventSerializer


def _user_can_manage_event(user, event):
    if user.is_admin:
        return True
    return (
        user.role == UserRole.ORGANIZER
        and event.organizer_id == user.id
    )


def _user_can_see_unpublished_event(user, event):
    if event.is_published:
        return True
    if not user.is_authenticated:
        return False
    if user.is_admin:
        return True
    return user.role == UserRole.ORGANIZER and event.organizer_id == user.id


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


def _get_filtered_events(request):
    events = Event.objects.filter(
        publish_status=EventPublishStatus.APPROVED,
        date__gte=timezone.now()
    ).prefetch_related("categories")

    search_query = request.GET.get("search", "").strip()
    selected_category = request.GET.get("category", "")
    location = request.GET.get("location", "").strip()
    max_price = request.GET.get("max_price", "")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    sort = request.GET.get("sort", "date")

    if search_query:
        events = events.filter(title__icontains=search_query)

    if selected_category:
        events = events.filter(categories__slug=selected_category)

    if location:
        events = events.filter(location__icontains=location)

    if max_price:
        try:
            events = events.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if start_date and end_date:
        events = events.filter(date__date__range=(start_date, end_date))
    else:
        if start_date:
            events = events.filter(date__date__gte=start_date)
        if end_date:
            events = events.filter(date__date__lte=end_date)

    if sort == "date_desc":
        events = events.order_by("-date")
    else:
        events = events.order_by("date")

    return events.distinct()


def event_list(request):
    events = _get_filtered_events(request)

    search_query = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '')
    location = request.GET.get('location', '').strip()
    sort = request.GET.get('sort', 'date')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    max_price = request.GET.get('max_price', '')

    paginator = Paginator(events, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': Category.objects.all(),
        'search_query': search_query,
        'selected_category': selected_category,
        'location': location,
        'sort': sort,
        'max_price': max_price,
        'start_date': start_date,
        'end_date': end_date,
        'filter_query_string': filter_query_string,
    }
    return render(request, 'events/event_list.html', context)


@api_view(["GET"])
def event_api_list(request):
    events = _get_filtered_events(request)
    serializer = EventSerializer(
        events,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


def event_page_api(request):
    events = _get_filtered_events(request)

    paginator = Paginator(events, 6)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    grid_html = render_to_string(
        "events/partials/event_page_grid.html",
        {
            "events": page_obj,
            "user": request.user,
        },
        request=request,
    )

    list_html = render_to_string(
        "events/partials/event_page_list.html",
        {
            "events": page_obj,
            "user": request.user,
        },
        request=request,
    )

    return JsonResponse({
        "grid_html": grid_html,
        "list_html": list_html,
        "has_next": page_obj.has_next(),
        "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
    })


def event_detail(request, pk):
    event = get_object_or_404(Event.objects.prefetch_related("categories"), pk=pk)

    if not _user_can_see_unpublished_event(request.user, event):
        raise PermissionDenied("This event is not publicly available.")

    user_has_booked = False
    if request.user.is_authenticated:
        user_has_booked = _user_has_booked_event(request.user, event)

    back_url, back_label = _resolve_back_navigation(request)

    return render(
        request,
        'events/event_detail.html',
        {
            'event': event,
            'user_has_booked': user_has_booked,
            'can_manage': (
                _user_can_manage_event(request.user, event)
                if request.user.is_authenticated
                else False
            ),
            'back_url': back_url,
            'back_label': back_label,
        },
    )


@attendee_required
def book_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        if not event.is_published:
            messages.error(request, 'This event is not published.')
            return redirect('event_detail', pk=pk)

        if event.is_expired:
            messages.error(request, 'This event has already occurred.')
            return redirect('event_detail', pk=pk)

        if event.is_sold_out:
            messages.error(request, 'This event is sold out.')
            return redirect('event_detail', pk=pk)

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        if quantity > event.tickets_remaining:
            messages.error(request, f'Only {event.tickets_remaining} tickets remaining.')
            return redirect('book_ticket', pk=pk)

        with transaction.atomic():
            event_locked = Event.objects.select_for_update().get(pk=pk)

            if event_locked.tickets_remaining < quantity:
                messages.error(request, f'Only {event_locked.tickets_remaining} tickets remaining.')
                return redirect('book_ticket', pk=pk)

            ticket, created = Ticket.objects.get_or_create(
                event=event_locked,
                attendee=request.user,
                defaults={'quantity': quantity},
            )
            if not created:
                ticket.quantity += quantity
                ticket.save(update_fields=['quantity'])

            EventBooking.objects.get_or_create(
                event=event_locked,
                user=request.user,
            )

            if event_locked.organizer:
                try:
                    Notification.objects.create(
                        recipient=event_locked.organizer,
                        event=event_locked,
                        title=f"New Booking: {event_locked.title}",
                        message=f"{request.user.username} just booked {quantity} ticket(s) for '{event_locked.title}'."
                    )
                except Exception as notif_err:
                    print(f"Failed to create booking notification: {notif_err}")

        try:
            send_booking_confirmation_email(ticket)
        except Exception as e:
            print(f"Failed to send booking confirmation email: {e}")

        messages.success(
            request,
            f'You have booked {quantity} ticket(s) for "{event.title}". A confirmation email has been sent.',
        )
        return redirect('my_bookings')

    return redirect('book_ticket', pk=pk)


@attendee_required
def book_ticket(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not event.is_published:
        messages.error(request, 'This event is not available for booking.')
        return redirect('event_detail', pk=pk)

    if event.is_expired:
        messages.error(request, 'This event has already occurred.')
        return redirect('event_detail', pk=pk)

    if event.is_sold_out:
        messages.error(request, 'This event is sold out.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        if quantity > event.tickets_remaining:
            messages.error(request, f'Only {event.tickets_remaining} tickets remaining.')
            return render(request, 'events/book_ticket.html', {'event': event})

        with transaction.atomic():
            event_locked = Event.objects.select_for_update().get(pk=pk)

            if event_locked.tickets_remaining < quantity:
                messages.error(request, f'Only {event_locked.tickets_remaining} tickets remaining.')
                return render(request, 'events/book_ticket.html', {'event': event})

            ticket, created = Ticket.objects.get_or_create(
                event=event_locked,
                attendee=request.user,
                defaults={'quantity': quantity},
            )
            if not created:
                ticket.quantity += quantity
                ticket.save(update_fields=['quantity'])

            EventBooking.objects.get_or_create(
                event=event_locked,
                user=request.user,
            )

            if event_locked.organizer:
                try:
                    Notification.objects.create(
                        recipient=event_locked.organizer,
                        event=event_locked,
                        title=f"New Booking: {event_locked.title}",
                        message=f"{request.user.username} just booked {quantity} ticket(s) for '{event_locked.title}'."
                    )
                except Exception as notif_err:
                    print(f"Failed to create booking notification: {notif_err}")

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


@organizer_or_admin_required
def event_create(request):
    """Create an event and assign the logged-in organizer as owner."""
    if not request.user.is_admin and request.user.is_organizer and not request.user.is_approved_organizer:
        messages.error(request, 'Your organizer account must be approved by an administrator before creating events.')
        return redirect('organizer_dashboard')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            form.save_m2m()
            messages.success(request, 'Event created successfully.')
            if request.user.is_admin:
                return redirect('admin_dashboard')
            return redirect('my_events')
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


@organizer_or_admin_required
def event_edit(request, pk):
    """Edit an event. Admins can edit any event, organizers only their own."""
    if request.user.is_admin:
        event = get_object_or_404(Event, pk=pk)
    else:
        event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            if request.user.is_admin:
                return redirect('admin_dashboard')
            return redirect('my_events')
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


@organizer_or_admin_required
def event_delete(request, pk):
    """Delete an event. Admins can delete any event, organizers only their own."""
    if request.user.is_admin or request.user.is_superuser:
        event = get_object_or_404(Event, pk=pk)
    else:
        event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        if request.user.is_admin or request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('my_events')

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


@login_required
def get_unread_notifications_api(request):
    """API endpoint to get the latest unread notifications for the logged in user."""
    notifications = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-created_at')
    unread_count = notifications.count()
    notifications_data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'created_at': n.created_at.strftime('%b %d, %H:%M'),
            'event_id': n.event_id,
        }
        for n in notifications[:5]
    ]
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data
    })


@login_required
def mark_notification_as_read(request, pk):
    """API endpoint to mark a specific notification as read."""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)


@login_required
def save_fcm_token(request):
    """Save the user's FCM token for push notifications."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            if token:
                request.user.fcm_token = token
                request.user.save()
                return JsonResponse({'status': 'success', 'message': 'Token saved successfully'})
            return JsonResponse({'status': 'error', 'message': 'No token provided'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


create_event = event_create
edit_event = event_edit
delete_event = event_delete
