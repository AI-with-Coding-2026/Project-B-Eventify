import json
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.shortcuts import redirect,  get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.models import Profile
from bookings.models import Booking

from .forms import EventForm
from .models import Event


def _is_organizer(user):
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"is_organizer": True})
    return profile.is_organizer


class HomeView(TemplateView):
    template_name = "home.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if _is_organizer(request.user):
                return redirect("events:event_list")
            return redirect("events:browse")
        return super().get(request, *args, **kwargs)


class OrganizerLoginView(LoginView):
    template_name = "events/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if _is_organizer(self.request.user):
            return str(reverse_lazy("events:event_list"))
        return str(reverse_lazy("events:browse"))


class OrganizerOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return _is_organizer(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return redirect("events:browse")


class OwnerRequiredMixin(OrganizerOnlyMixin):
    def test_func(self):
        if not _is_organizer(self.request.user):
            return False
        obj = self.get_object()
        return obj.organizer_id == self.request.user.id

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "You don't have permission to access that event.")
        return redirect("events:event_list")


class EventListView(OrganizerOnlyMixin, ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user)


class PublicEventBrowseView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "events/browse_events.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        return Event.objects.select_related("organizer").order_by("date")

class BookEventView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if _is_organizer(request.user):
            messages.error(request, "Organizer accounts can't book tickets.")
            return redirect("events:browse")

        event = get_object_or_404(Event, pk=pk)
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 1:
            messages.error(request, "Enter a valid number of tickets.")
        elif quantity > event.tickets_remaining:
            messages.error(
                request,
                f"Only {event.tickets_remaining} ticket(s) left for {event.title}.",
            )
        else:
            Booking.objects.create(
                event=event,
                user=request.user,
                customer_name=request.user.get_username(),
                customer_email=request.user.email or f"{request.user.username}@example.local",
                quantity=quantity,
            )
            messages.success(request, f"Booked {quantity} ticket(s) for {event.title}.")
            return redirect("events:my_bookings")

        return redirect("events:browse")


class MyBookingsView(LoginRequiredMixin, ListView):
    template_name = "events/my_bookings.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("event")



class EventCreateView(OrganizerOnlyMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_url = reverse_lazy("events:event_list")

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        messages.success(self.request, "Event created.")
        return super().form_valid(form)


class EventUpdateView(OwnerRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_url = reverse_lazy("events:event_list")

    def form_valid(self, form):
        if "poster_image" in form.changed_data:
            old = Event.objects.filter(pk=self.object.pk).first()
            if old and old.poster_image and old.poster_image != form.instance.poster_image:
                old.poster_image.delete(save=False)
        messages.success(self.request, "Event updated.")
        return super().form_valid(form)


class EventDeleteView(OwnerRequiredMixin, DeleteView):
    model = Event
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy("events:event_list")

    def form_valid(self, form):
        messages.success(self.request, "Event deleted.")
        return super().form_valid(form)


class DashboardView(OrganizerOnlyMixin, TemplateView):
    template_name = "events/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = Event.objects.filter(organizer=self.request.user).annotate(
            sold=Sum("bookings__quantity")
        )

        rows = []
        total_sold = 0
        total_revenue = 0
        total_max_tickets = 0
        for event in events:
            sold = event.sold or 0
            remaining = max(event.max_tickets - sold, 0)
            revenue = event.ticket_price * sold
            total_sold += sold
            total_revenue += revenue
            total_max_tickets += event.max_tickets
            rows.append(
                {
                    "event": event,
                    "sold": sold,
                    "remaining": remaining,
                    "revenue": revenue,
                }
            )

        context["rows"] = rows
        context["total_events"] = len(rows)
        context["total_sold"] = total_sold
        context["total_revenue"] = total_revenue
        context["total_remaining"] = max(total_max_tickets - total_sold, 0)
        context["chart_labels"] = json.dumps([row["event"].title for row in rows])
        context["chart_sold"] = json.dumps([row["sold"] for row in rows])
        context["chart_revenue"] = json.dumps([float(row["revenue"]) for row in rows])
        return context