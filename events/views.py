from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import (
    admin_required,
    attendee_required,
    organizer_required,
    role_required,
)
from authentication.models import UserRole
from .forms import CategoryForm, EventForm
from .models import Category, Event, EventBooking, Ticket


def _user_can_manage_event(user, event):
    if user.is_admin:
        return True
    return (
        user.role == UserRole.ORGANIZER
        and event.organizer_id == user.id
    )


def event_list(request):
    events = Event.objects.all().order_by('date')

    search_query = request.GET.get('search', '')
    selected_category = request.GET.get('category', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    max_price = request.GET.get('max_price', '')

    if search_query:
        events = events.filter(title__icontains=search_query)

    if selected_category:
        events = events.filter(category=selected_category)

    if max_price:
        events = events.filter(price__lte=max_price)

    if start_date and end_date:
        events = events.filter(date__date__range=(start_date, end_date))
    else:
        if start_date:
            events = events.filter(date__date__gte=start_date)
        if end_date:
            events = events.filter(date__date__lte=end_date)

    context = {
        'events': events,
        'categories': Event.CATEGORY_CHOICES,
        'search_query': search_query,
        'selected_category': selected_category,
        'max_price': max_price,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    user_has_booked = False

    if user.is_authenticated:
        user_has_booked = EventBooking.objects.filter(
            user=user,
            event=event,
        ).exists()

    context = {
        'event': event,
        'can_manage': user.is_authenticated and _user_can_manage_event(user, event),
        'can_book': (
            user.is_authenticated
            and user.role == UserRole.ATTENDEE
            and not user_has_booked
            and not event.is_sold_out
        ),
        'user_has_booked': user_has_booked,
    }
    return render(request, 'events/event_detail.html', context)


@role_required(UserRole.ATTENDEE)
def book_event(request, pk):
    if request.method != 'POST':
        return redirect('event_detail', pk=pk)

    event = get_object_or_404(Event, pk=pk)

    if EventBooking.objects.filter(user=request.user, event=event).exists():
        messages.info(request, f'You have already booked "{event.title}".')
        return redirect('event_detail', pk=pk)

    if event.is_sold_out:
        messages.error(request, 'This event is fully booked.')
        return redirect('event_detail', pk=pk)

    EventBooking.objects.create(user=request.user, event=event)
    messages.success(request, f'Successfully booked "{event.title}".')
    return redirect('event_detail', pk=pk)


@attendee_required
def book_ticket(request, pk):
    """Allow attendees to book a ticket for an event."""
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1

        Ticket.objects.create(
            event=event,
            attendee=request.user,
            quantity=quantity,
        )
        messages.success(
            request,
            f'Ticket booked for "{event.title}".',
        )
        return redirect('my_tickets')

    return render(
        request,
        'events/book_ticket.html',
        {'event': event},
    )


@attendee_required
def my_tickets(request):
    """Show tickets booked by the logged-in attendee."""
    tickets = (
        Ticket.objects.filter(attendee=request.user)
        .select_related('event')
        .order_by('-booked_at')
    )
    return render(
        request,
        'events/my_tickets.html',
        {'tickets': tickets},
    )


@organizer_required
def organizer_event_list(request):
    """Show only events owned by the logged-in organizer."""
    events = Event.objects.filter(organizer=request.user).order_by('-date')
    return render(
        request,
        'events/organizer_event_list.html',
        {'events': events},
    )


@organizer_required
def event_create(request):
    """Create an event and assign the logged-in organizer as owner."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully.')
            return redirect('organizer_event_list')
    else:
        form = EventForm()

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'page_title': 'Create Event',
            'submit_label': 'Create Event',
        },
    )


@organizer_required
def event_edit(request, pk):
    """Edit an event only if it belongs to the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            return redirect('organizer_event_list')
    else:
        form = EventForm(instance=event)

    return render(
        request,
        'events/event_form.html',
        {
            'form': form,
            'event': event,
            'page_title': 'Edit Event',
            'submit_label': 'Update Event',
        },
    )


@organizer_required
def event_delete(request, pk):
    """Delete an event only if it belongs to the logged-in organizer."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('organizer_event_list')

    return render(
        request,
        'events/event_confirm_delete.html',
        {'event': event},
    )


@admin_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'events/category_list.html', {'categories': categories})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.',
            )

            return redirect('category_create')

    else:
        form = CategoryForm()

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            'page_title': 'Create Category',
            'submit_label': 'Save Category',
        },
    )


@admin_required
def category_update(request, pk):
    """Allow admins to edit an existing category name/description."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category updated successfully.'
            )

            return redirect('category_update', pk=category.pk)

    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            'category': category,
            'page_title': 'Edit Category',
            'submit_label': 'Update Category',
        },
    )


@admin_required
def category_delete(request, pk):
    """Allow admins to delete an existing category after confirmation."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()
        messages.success(
            request,
            'Category deleted successfully.'
        )
        return redirect('category_list')

    return render(
        request,
        'events/category_confirm_delete.html',
        {'category': category},
    )


@role_required(UserRole.ORGANIZER)
def my_events(request):
    events = Event.objects.filter(
        organizer=request.user
    )

    return render(
        request,
        "events/my_events.html",
        {
            "events": events,
        },
    )


@role_required(UserRole.ORGANIZER)
def create_event(request):
    if request.method == "POST":
        form = EventForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            messages.success(
                request,
                "Event created successfully.",
            )

            return redirect("my_events")

    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "page_title": "Create Event",
            "submit_label": "Create Event",
        },
    )


@role_required(UserRole.ORGANIZER)
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not _user_can_manage_event(request.user, event):
        raise PermissionDenied

    if request.method == "POST":
        form = EventForm(
            request.POST,
            request.FILES,
            instance=event,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Event updated successfully.",
            )

            return redirect(
                "event_detail",
                pk=event.pk,
            )

    else:
        form = EventForm(
            instance=event
        )

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "event": event,
            "page_title": "Edit Event",
            "submit_label": "Update Event",
        },
    )


@role_required(UserRole.ORGANIZER)
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not _user_can_manage_event(request.user, event):
        raise PermissionDenied

    if request.method == "POST":
        event.delete()

        messages.success(
            request,
            "Event deleted successfully.",
        )

        if request.user.is_admin:
            return redirect("event_list")

        return redirect("my_events")

    return render(
        request,
        "events/event_confirm_delete.html",
        {
            "event": event,
        },
    )
