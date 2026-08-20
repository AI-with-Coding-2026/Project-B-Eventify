from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView

from events.models import Event

from .forms import CustomUserCreationForm, StyledAuthenticationForm


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('login')


@login_required
def dashboard(request):
    user_events = Event.objects.filter(
        organizer=request.user,
    ).order_by('date')

    upcoming_events = user_events.filter(
        date__gte=timezone.now(),
    )[:3]

    return render(
        request,
        'accounts/dashboard.html',
        {
            'user_events': user_events,
            'upcoming_events': upcoming_events,
        },
    )


login_view = LoginView.as_view(
    template_name='accounts/login.html',
    form_class=StyledAuthenticationForm,
)
logout_view = LogoutView.as_view(next_page=reverse_lazy('login'))
