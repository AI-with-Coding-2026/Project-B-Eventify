from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required, role_required
from .forms import StudentEditForm, UserRegistrationForm
from .models import User, UserRole
from events.models import Event


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
    return render(request, 'authentication/organizer_dashboard.html')


@role_required(UserRole.ADMIN, UserRole.ATTENDEE)
def attendee_dashboard(request):
    events = Event.objects.all()
    return render(
        request,
        'authentication/attendee_dashboard.html',
        {'events': events},
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
