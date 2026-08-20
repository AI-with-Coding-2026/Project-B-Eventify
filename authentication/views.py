from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from events.models import Category, Event, EventBooking, Ticket
from .decorators import admin_required, role_required

from decimal import Decimal
import json

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
    return render(request, 'authentication/home.html')

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
        'bookings': EventBooking.objects.select_related('user', 'event').order_by('-booked_at'),
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

@role_required(UserRole.ATTENDEE)
def attendee_dashboard(request):
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:3]
    return render(request, 'authentication/attendee_dashboard.html', {
        'upcoming_events': upcoming_events,
    })

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


# 2. دالة إغلاق/إلغاء الحجز (دالة مستقلة تبدأ من بداية السطر)
@role_required(UserRole.ATTENDEE)
def cancel_booking(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, attendee=request.user)

    if request.method == 'POST':
        try:
            cancel_quantity = int(request.POST.get('cancel_quantity', ticket.quantity))
        except (TypeError, ValueError):
            cancel_quantity = ticket.quantity

        if cancel_quantity < 1 or cancel_quantity > ticket.quantity:
            messages.error(request, 'Invalid ticket quantity to cancel.')
            return redirect('cancel_booking', pk=pk)

        if cancel_quantity >= ticket.quantity:
            ticket.delete()
            messages.success(request, 'Booking cancelled successfully.')
        else:
            ticket.quantity -= cancel_quantity
            ticket.save()
            messages.success(
                request,
                f'Cancelled {cancel_quantity} ticket(s). {ticket.quantity} remaining.',
            )

        return redirect('my_bookings')

    return render(request, 'authentication/booking_confirm_cancel.html', {
        'ticket': ticket,
        'quantity_range': range(1, ticket.quantity + 1),
    })