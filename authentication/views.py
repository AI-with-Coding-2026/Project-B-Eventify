from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render

from .decorators import admin_required
from .forms import UserRegistrationForm
from .models import User, UserRole


# -------------------------
# Registration
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
            form.save()
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
    return render(
        request,
        'authentication/register_success.html'
    )


@login_not_required
def home(request):
    return render(
        request,
        'authentication/home.html'
    )


# -------------------------
# Admin
# -------------------------

@admin_required
def admin_dashboard(request):
    users = User.objects.all()

    context = {
        'total_users': users.count(),
        'admin_count': users.filter(role=UserRole.ADMIN).count(),
        'organizer_count': users.filter(role=UserRole.ORGANIZER).count(),
        'attendee_count': users.filter(role=UserRole.ATTENDEE).count(),
    }

    return render(
        request,
        'authentication/admin_dashboard.html',
        context
    )


# -------------------------
# Login
# -------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            if user.is_admin:
                return redirect('admin_dashboard')
            elif user.is_organizer:
                return redirect('organizer_dashboard')
            else:
                return redirect('attendee_dashboard')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(
        request,
        'authentication/login.html'
    )


# -------------------------
# Logout
# -------------------------

def logout_view(request):
    logout(request)
    return redirect('home')


# -------------------------
# Unauthorized
# -------------------------

def unauthorized(request):
    return render(
        request,
        'authentication/unauthorized.html'
    )


# -------------------------
# Organizer Dashboard
# -------------------------

def organizer_dashboard(request):
    return render(
        request,
        'authentication/organizer_dashboard.html'
    )


# -------------------------
# Attendee Dashboard
# -------------------------

def attendee_dashboard(request):
    return render(
        request,
        'authentication/attendee_dashboard.html'
    )