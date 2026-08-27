from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from decimal import Decimal

from .decorators import admin_required, role_required
from .forms import StudentEditForm, UserRegistrationForm
from .models import User, UserRole
from events.models import Category, Event


# -------------------------
# Person 1:
# -------------------------

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

            # Auto-login after successful registration.
            login(request, user)

            messages.success(
                request,
                'Your account was created successfully.',
            )

            # Redirect to the role-appropriate dashboard.
            if user.is_admin:
                return redirect('admin_dashboard')
            if user.is_organizer:
                return redirect('organizer_dashboard')
            return redirect('attendee_dashboard')

    else:
        form = UserRegistrationForm()


    return render(
        request,
        'authentication/register.html',
        {'form': form}
    )


@login_not_required
def home(request):
    return render(request, 'authentication/home.html')


@admin_required
def admin_dashboard(request):
    users = User.objects.all()
    context = {
        'total_users': users.count(),
        'admin_count': users.filter(role=UserRole.ADMIN).count(),
        'organizer_count': users.filter(role=UserRole.ORGANIZER).count(),
        'attendee_count': users.filter(role=UserRole.ATTENDEE).count(),
    }
    return render(request, 'authentication/admin_dashboard.html', context)


@login_not_required
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin_dashboard')
        if request.user.is_organizer:
            return redirect('organizer_dashboard')
        return redirect('attendee_dashboard')

    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is None:
            messages.error(request, 'Invalid username or password.')
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
    messages.success(request, 'You have been logged out.')
    return redirect('login')


def unauthorized(request):
    return render(request, 'authentication/unauthorized.html')


@role_required(UserRole.ADMIN, UserRole.ORGANIZER)
def organizer_dashboard(request):
    """Analytics dashboard showing ticket sales performance for organizer's events."""
    if request.user.is_admin:
        events = Event.objects.all()
    else:
        events = Event.objects.filter(organizer=request.user)

    events = events.annotate(
        tickets_sold=Coalesce(Sum('bookings__quantity'), 0),
    )

    # Build per-event stats
    event_stats = []
    total_tickets_sold = 0
    total_revenue = Decimal('0.00')

    for event in events:
        sold = event.tickets_sold
        remaining = event.max_tickets - sold
        revenue = event.ticket_price * sold
        sell_percentage = int((sold / event.max_tickets) * 100) if event.max_tickets > 0 else 0
        total_tickets_sold += sold
        total_revenue += revenue
        event_stats.append({
            'event': event,
            'tickets_sold': sold,
            'tickets_remaining': remaining,
            'revenue': revenue,
            'sell_percentage': sell_percentage,
        })

    context = {
        'event_stats': event_stats,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
        'total_events': len(event_stats),
    }
    return render(request, 'authentication/organizer_dashboard.html', context)


@role_required(UserRole.ADMIN, UserRole.ATTENDEE)
def attendee_dashboard(request):
    """Browse upcoming events with sorting, filtering, and infinite scroll."""
    now = timezone.now()

    # Feature 2: Only show upcoming events (exclude past/concluded events)
    events = Event.objects.filter(date__gte=now)

    # Feature 6: Annotate with tickets_sold for available ticket display
    events = events.annotate(
        tickets_sold=Coalesce(Sum('bookings__quantity'), 0),
    )

    # Compute tickets_remaining via Python after fetch (F() subtraction
    # on PositiveIntegerField can cause issues, so we do it simply)

    # Feature 3: Location filtering
    location_query = request.GET.get('location', '').strip()
    if location_query:
        events = events.filter(location__icontains=location_query)

    # Feature 3: Category filtering
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        events = events.filter(categories__slug=category_slug).distinct()

    # Feature 3: Chronological sorting
    sort = request.GET.get('sort', 'date_asc').strip()
    if sort == 'date_desc':
        events = events.order_by('-date')
    else:
        events = events.order_by('date')  # Upcoming first (default)

    # Gather filter options for the UI
    all_categories = Category.objects.all()

    # Feature 8: Pagination (6 events per page)
    paginator = Paginator(events, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # AJAX request for infinite scroll
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string(
            'authentication/_event_card_fragment.html',
            {'events': page_obj, 'user': request.user},
            request=request,
        )
        return JsonResponse({
            'html': html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        })

    return render(
        request,
        'authentication/attendee_dashboard.html',
        {
            'events': page_obj,
            'page_obj': page_obj,
            'all_categories': all_categories,
            'location_query': location_query,
            'category_slug': category_slug,
            'current_sort': sort,
        },
    )


# -------------------------
# Student Management (Admin)
# -------------------------

@admin_required
def student_list(request):
    """List all users with optional search and role filter."""
    users = User.objects.all().order_by('-date_joined')

    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    # Role filter
    role_filter = request.GET.get('role', '').strip()
    if role_filter and role_filter in dict(UserRole.choices):
        users = users.filter(role=role_filter)

    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'role_choices': UserRole.choices,
    }
    return render(request, 'authentication/student_list.html', context)


@admin_required
def student_detail(request, pk):
    """Show read-only details for a single user."""
    student = get_object_or_404(User, pk=pk)
    return render(
        request,
        'authentication/student_detail.html',
        {'student': student},
    )


@admin_required
def student_edit(request, pk):
    """Edit a user's profile information."""
    student = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        form._request_user = request.user
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Student "{student.full_name}" updated successfully!',
            )
            return redirect('student_list')
    else:
        form = StudentEditForm(instance=student)

    return render(
        request,
        'authentication/student_edit.html',
        {
            'form': form,
            'student': student,
        },
    )


@admin_required
def student_delete(request, pk):
    """Delete a user after confirmation."""
    student = get_object_or_404(User, pk=pk)

    # Prevent admins from deleting themselves
    if student == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('student_list')

    # Prevent deleting superusers
    if student.is_superuser:
        messages.error(request, 'Superuser accounts cannot be deleted.')
        return redirect('student_list')

    if request.method == 'POST':
        name = student.full_name
        student.delete()
        messages.success(request, f'Student "{name}" deleted successfully!')
        return redirect('student_list')

    return render(
        request,
        'authentication/student_confirm_delete.html',
        {'student': student},
    )
