from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render

from .decorators import admin_required
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
            form.save()
            return redirect('register_success')
    else:
        form = UserRegistrationForm()

    return render(request, 'authentication/register.html', {'form': form})


@login_not_required
def register_success(request):
    return render(request, 'authentication/register_success.html')


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
