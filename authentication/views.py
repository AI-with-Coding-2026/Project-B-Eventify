from django.contrib.auth.decorators import login_not_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import UserRegistrationForm
from .models import UserRole


# -------------------------
# Person 1:
# -------------------------

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


    return render(
        request,
        'authentication/register.html',
        {'form': form}
    )



@login_not_required
def register_success(request):
    return render(request, 'authentication/register_success.html')


## Template pages views




def home(request):
    return render(request, 'base.html')

    return render(
        request,
        'authentication/register_success.html'
    )



# -------------------------
# Person 2: 
# -------------------------

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(request, user)


            # Role available after login
            if user.is_admin:
                return redirect('admin:index')

            elif user.is_organizer:
                return redirect('organizer_dashboard')

            elif user.is_attendee:
                return redirect('attendee_dashboard')


        else:

            messages.error(
                request,
                "Invalid username or password"
            )


    return render(
        request,
        'authentication/login.html'
    )



def logout_view(request):

    logout(request)

    return redirect('login')


# -------------------------
# Role-based access control
# -------------------------

def unauthorized(request):
    return render(request, 'authentication/unauthorized.html', status=403)


@role_required(UserRole.ORGANIZER)
def organizer_dashboard(request):
    return render(request, 'authentication/organizer_dashboard.html')


@role_required(UserRole.ATTENDEE)
def attendee_dashboard(request):
    return render(request, 'authentication/attendee_dashboard.html')
