from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import UserRegistrationForm


@login_not_required
def register(request):
    if request.user.is_authenticated:
        return redirect('admin:index')

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


## Template pages views




def home(request):
    return render(request, 'base.html')