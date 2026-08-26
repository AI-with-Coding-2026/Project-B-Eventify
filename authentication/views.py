import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_not_required, login_required
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from events.models import Category, Event, EventBooking, Ticket
from events.exports import export_events_excel, export_events_pdf

from .decorators import admin_required, organizer_required, role_required
from .forms import UserRegistrationForm
from .models import User, UserRole


@login_not_required
def register(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('register_success')
    else:
        form = UserRegistrationForm()

    return render(
        request,
        'authentication/register.html',
        {'form': form}
    )


@login_not_required
def register_success(request):
    return render(request, 'authentication/register_success.html')


@login_not_required
def home(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        elif request.user.is_organizer:
            return redirect('organizer_dashboard')
        elif request.user.is_attendee:
            return redirect('attendee_dashboard')

    featured_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]
    return render(request, 'authentication/home.html', {'featured_events': featured_events})


@admin_required
def admin_dashboard(request):
    users = User.objects.all()
    organizers = users.filter(role=UserRole.ORGANIZER)
    attendees = users.filter(role=UserRole.ATTENDEE)
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:3]
    context = {
        'total_users': users.count(),
        'admin_count': users.filter(role=UserRole.ADMIN).count(),
        'organizer_count': organizers.count(),
        'attendee_count': attendees.count(),
        'organizers': organizers.order_by('username'),
        'attendees': attendees.order_by('username'),
        'events': Event.objects.select_related('organizer').order_by('date'),
        'tickets': Ticket.objects.select_related('attendee', 'event').order_by('-booked_at'),
        'bookings': sorted(
    list(Ticket.objects.select_related('attendee', 'event')) +
    list(EventBooking.objects.select_related('user', 'event')),
    key=lambda b: b.booked_at,
    reverse=True,
),
        'categories': Category.objects.order_by('name'),
        'upcoming_events': upcoming_events,
    }
    return render(request, 'authentication/admin_dashboard.html', context)


@admin_required
def user_delete(request, pk):
    """Allow admins to delete organizers and attendees after confirmation."""
    target = get_object_or_404(User, pk=pk)

    if target.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_dashboard')

    if target.role == UserRole.ADMIN:
        messages.error(request, 'Admin accounts cannot be deleted from the dashboard.')
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = target.username
        target.delete()
        messages.success(request, f'User "{username}" deleted successfully.')
        return redirect('admin_dashboard')

    return render(
        request,
        'authentication/user_confirm_delete.html',
        {'target_user': target},
    )


@login_not_required
def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is None:
            messages.error(request, 'Invalid username or password')
        else:
            login(request, user)
            if user.is_admin:
                return redirect('admin_dashboard')
            if user.is_organizer:
                return redirect('organizer_dashboard')
            return redirect('attendee_dashboard')

    return render(request, 'authentication/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def unauthorized(request):
    return render(request, 'authentication/unauthorized.html', status=403)


@role_required(UserRole.ORGANIZER)

@organizer_required
def organizer_dashboard(request):
    """Dashboard showing ticket sales performance, revenue, and charts for the organizer's events."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:3]

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = sum((event.revenue for event in events), Decimal('0.00'))

    # Chronological order for chart rendering (oldest to newest)
    chart_events = list(reversed(list(events)))
    chart_labels = [e.title for e in chart_events]
    chart_tickets_sold = [e.tickets_sold for e in chart_events]
    chart_tickets_remaining = [e.tickets_remaining for e in chart_events]
    chart_revenue = [float(e.revenue) for e in chart_events]

    context = {
        'upcoming_events': upcoming_events,
        'events': events,
        'total_events': total_events,
        'total_tickets_sold': total_tickets_sold,
        'total_tickets_remaining': total_tickets_remaining,
        'total_revenue': total_revenue,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_tickets_sold_json': json.dumps(chart_tickets_sold),
        'chart_tickets_remaining_json': json.dumps(chart_tickets_remaining),
        'chart_revenue_json': json.dumps(chart_revenue),
    }
    return render(request, 'authentication/organizer_dashboard.html', context)


@organizer_required
def organizer_dashboard_stats_api(request):
    """JSON API endpoint returning live statistics and chart data for the organizer's events."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')

    upcoming_events = Event.objects.filter(
    date__gte=timezone.now()
    ).order_by('date')[:3]

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = float(sum((event.revenue for event in events), Decimal('0.00')))

    chart_events = list(reversed(list(events)))
    chart_labels = [e.title for e in chart_events]
    chart_tickets_sold = [e.tickets_sold for e in chart_events]
    chart_tickets_remaining = [e.tickets_remaining for e in chart_events]
    chart_revenue = [float(e.revenue) for e in chart_events]

    events_data = [
        {
            'pk': e.pk,
            'title': e.title,
            'price': str(e.price),
            'tickets_sold': e.tickets_sold,
            'tickets_remaining': e.tickets_remaining,
            'max_tickets': e.max_tickets,
            'revenue': float(e.revenue),
            'is_sold_out': e.is_sold_out,
        }
        for e in events
    ]

    return JsonResponse({
        'total_events': total_events,
        'total_tickets_sold': total_tickets_sold,
        'total_tickets_remaining': total_tickets_remaining,
        'total_revenue': total_revenue,
        'chart_labels': chart_labels,
        'chart_tickets_sold': chart_tickets_sold,
        'chart_tickets_remaining': chart_tickets_remaining,
        'chart_revenue': chart_revenue,
        'events': events_data,
    })


@login_required
def organizer_export_excel(request):
    """Download Excel (.xlsx) export of event analytics for organizers or admins."""
    if not (request.user.is_organizer or request.user.is_admin):
        return redirect('unauthorized')

    if request.user.is_admin:
        organizer_id = request.GET.get('organizer')
        if organizer_id:
            events = Event.objects.filter(organizer_id=organizer_id).order_by('-date')
        else:
            events = Event.objects.all().order_by('-date')
    else:
        events = Event.objects.filter(organizer=request.user).order_by('-date')

    return export_events_excel(events, user=request.user)


@login_required
def organizer_export_pdf(request):
    """Download styled PDF analytics report with revenue metrics, charts, and key stats."""
    if not (request.user.is_organizer or request.user.is_admin):
        return redirect('unauthorized')

    if request.user.is_admin:
        organizer_id = request.GET.get('organizer')
        if organizer_id:
            events = Event.objects.filter(organizer_id=organizer_id).order_by('-date')
        else:
            events = Event.objects.all().order_by('-date')
    else:
        events = Event.objects.filter(organizer=request.user).order_by('-date')

    total_events = events.count()
    total_tickets_sold = sum(event.tickets_sold for event in events)
    total_tickets_remaining = sum(event.tickets_remaining for event in events)
    total_revenue = sum((event.revenue for event in events), Decimal('0.00'))

    return export_events_pdf(
        events=events,
        total_events=total_events,
        total_tickets_sold=total_tickets_sold,
        total_tickets_remaining=total_tickets_remaining,
        total_revenue=total_revenue,
        user=request.user,
    )


@role_required(UserRole.ATTENDEE)
def attendee_dashboard(request):
    now = timezone.now()
    featured_events = Event.objects.filter(date__gte=now).order_by('date')[:5]

    tickets = (
        Ticket.objects.filter(attendee=request.user)
        .select_related('event')
    )
    legacy_bookings = (
        EventBooking.objects.filter(user=request.user)
        .select_related('event')
    )

    upcoming_tickets = list(
        tickets.filter(event__date__gte=now).order_by('event__date')
    )
    upcoming_legacy = [
        b for b in legacy_bookings.filter(event__date__gte=now).order_by('event__date')
        if not any(t.event_id == b.event_id for t in upcoming_tickets)
    ]

    upcoming_bookings = sorted(
        upcoming_tickets + upcoming_legacy,
        key=lambda x: x.event.date,
    )
    next_booking = upcoming_bookings[0] if upcoming_bookings else None

    return render(request, 'authentication/attendee_dashboard.html', {
        'featured_events': featured_events,
        'upcoming_events': featured_events,
        'upcoming_bookings': upcoming_bookings,
        'next_booking': next_booking,
    })


@admin_required
def admin_user_list(request):
    users = User.objects.exclude(pk=request.user.pk).order_by('username')
    return render(request, 'authentication/admin_user_list.html', {'users': users})


@role_required(UserRole.ATTENDEE)
def my_bookings(request):
    now = timezone.now()
    tickets = (
        Ticket.objects.filter(attendee=request.user)
        .select_related('event')
    )
    legacy_bookings = (
        EventBooking.objects.filter(user=request.user)
        .select_related('event')
    )

    upcoming_tickets = list(
        tickets.filter(event__date__gte=now).order_by('event__date')
    )
    past_tickets = list(
        tickets.filter(event__date__lt=now).order_by('-event__date')
    )

    upcoming_legacy = [
        b for b in legacy_bookings.filter(event__date__gte=now).order_by('event__date')
        if not any(t.event_id == b.event_id for t in upcoming_tickets)
    ]
    past_legacy = [
        b for b in legacy_bookings.filter(event__date__lt=now).order_by('-event__date')
        if not any(t.event_id == b.event_id for t in past_tickets)
    ]

    upcoming_bookings = sorted(
        upcoming_tickets + upcoming_legacy,
        key=lambda x: x.event.date,
    )
    past_bookings = sorted(
        past_tickets + past_legacy,
        key=lambda x: x.event.date,
        reverse=True,
    )

    next_booking = upcoming_bookings[0] if upcoming_bookings else None

    return render(request, 'authentication/my_bookings.html', {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'total_bookings': len(upcoming_bookings) + len(past_bookings),
        'next_booking': next_booking,
    })


@role_required(UserRole.ATTENDEE)
def cancel_booking(request, pk):
    ticket = Ticket.objects.filter(pk=pk, attendee=request.user).first()
    legacy_booking = None
    if not ticket:
        legacy_booking = EventBooking.objects.filter(pk=pk, user=request.user).first()
        if not legacy_booking:
            messages.info(request, 'This booking has already been cancelled.')
            return redirect('attendee_dashboard')

    if request.method == 'POST':
        if ticket:
            try:
                cancel_quantity = int(request.POST.get('cancel_quantity', ticket.quantity))
            except (TypeError, ValueError):
                cancel_quantity = ticket.quantity

            if cancel_quantity < 1 or cancel_quantity > ticket.quantity:
                messages.error(request, 'Invalid ticket quantity to cancel.')
                return redirect('cancel_booking', pk=pk)

            if cancel_quantity >= ticket.quantity:
                EventBooking.objects.filter(user=ticket.attendee, event=ticket.event).delete()
                ticket.delete()
                messages.success(request, 'Booking cancelled successfully.')
            else:
                ticket.quantity -= cancel_quantity
                ticket.save()
                messages.success(
                    request,
                    f'Cancelled {cancel_quantity} ticket(s). {ticket.quantity} remaining.',
                )
        elif legacy_booking:
            Ticket.objects.filter(attendee=legacy_booking.user, event=legacy_booking.event).delete()
            legacy_booking.delete()
            messages.success(request, 'Booking cancelled successfully.')

        return redirect('attendee_dashboard')

    booking_obj = ticket if ticket else legacy_booking
    quantity = getattr(booking_obj, 'quantity', 1)
    return render(request, 'authentication/booking_confirm_cancel.html', {
        'ticket': booking_obj,
        'quantity_range': range(1, quantity + 1),
    })

@admin_required
def analytics_dashboard(request):
    organizer_id = request.GET.get('organizer')

    tickets = Ticket.objects.select_related('event', 'event__organizer')

    if organizer_id:
        tickets = tickets.filter(event__organizer_id=organizer_id)

    total_revenue = tickets.aggregate(
        total=Coalesce(
            Sum(F('quantity') * F('event__price'), output_field=DecimalField()),
            0,
            output_field=DecimalField(),
        )
    )['total']

    total_bookings = tickets.count()
    total_tickets_sold = tickets.aggregate(total=Coalesce(Sum('quantity'), 0))['total']

    events_qs = Event.objects.all()
    if organizer_id:
        events_qs = events_qs.filter(organizer_id=organizer_id)
    total_events = events_qs.count()

    filtered_events = list(events_qs.select_related('organizer').annotate(
        event_tickets_sold=Coalesce(Sum('tickets__quantity'), 0),
        event_revenue=Coalesce(
            Sum(
                F('tickets__quantity') * F('price'),
                output_field=DecimalField(),
            ),
            0,
            output_field=DecimalField(),
        ),
    ).order_by('-date', 'title'))
    total_rev_float = float(total_revenue) if total_revenue else 0.0
    event_chart_data = [
        {
            'id': event.pk,
            'title': event.title,
            'organizer': event.organizer.username if event.organizer else '—',
            'category': event.category_label,
            'date': event.date.strftime('%b %d, %Y') if event.date else 'TBA',
            'location': event.location or 'TBA',
            'price': float(event.price),
            'revenue': float(event.event_revenue),
            'tickets': event.event_tickets_sold,
            'percentage': round((float(event.event_revenue) / total_rev_float * 100), 1) if total_rev_float > 0 else 0,
        }
        for event in filtered_events
    ]

    organizers = User.objects.filter(role=UserRole.ORGANIZER).order_by('username')
    categories = sorted({event.category_label for event in filtered_events if event.category_label})

    context = {
        'total_revenue': total_revenue,
        'total_bookings': total_bookings,
        'total_tickets_sold': total_tickets_sold,
        'total_events': total_events,
        'filtered_events': filtered_events,
        'event_chart_data': event_chart_data,
        'organizers': organizers,
        'categories': categories,
        'selected_organizer': organizer_id,
    }
    return render(request, 'authentication/analytics_dashboard.html', context)