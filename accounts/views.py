from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import RegisterForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"

    def get_success_url(self):
        if self.object.profile.is_organizer:
            return str(reverse_lazy("events:event_list"))
        return str(reverse_lazy("events:browse"))

    def form_valid(self, form):
        response = super().form_valid(form)
        profile = self.object.profile
        profile.is_organizer = form.cleaned_data["role"] == "organizer"
        profile.save()
        login(self.request, self.object)
        return response