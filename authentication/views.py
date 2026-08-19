from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from events.models import Category, Event, EventBooking, Ticket

from .decorators import admin_required, role_required
from .forms import UserRegistrationForm
from .models import User, UserRole
from decimal import Decimal

from django.db.models import Count

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
def organizer_dashboard(request):
    """Show ticket sales performance for events owned by the logged-in organizer."""
    my_events = (
        Event.objects.filter(organizer=request.user)
        .annotate(tickets_sold=Count('bookings'))
        .order_by('-date')
    )

    total_tickets_sold = 0
    total_revenue = Decimal('0.00')
    event_stats = []

    for event in my_events:
        sold = event.tickets_sold
        remaining = max(event.max_tickets - sold, 0)
        revenue = event.price * sold

        total_tickets_sold += sold
        total_revenue += revenue

        event_stats.append({
            'event': event,
            'tickets_sold': sold,
            'tickets_remaining': remaining,
            'revenue': revenue,
        })

    return render(request, 'authentication/organizer_dashboard.html', {
        'event_stats': event_stats,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
    })


@role_required(UserRole.ADMIN, UserRole.ATTENDEE)
def attendee_dashboard(request):
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:3]
    return render(request, 'authentication/attendee_dashboard.html', {
        'upcoming_events': upcoming_events,
    })
