from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CustomUserCreationForm, StyledAuthenticationForm


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')


login_view = LoginView.as_view(
    template_name='accounts/login.html',
    form_class=StyledAuthenticationForm,
)
logout_view = LogoutView.as_view(next_page=reverse_lazy('login'))
