from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import (
    admin_required,
    attendee_required,
    organizer_required,
)

from .forms import CategoryForm, EventForm
from .models import Category, Event, Ticket


def event_list(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


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
    """Display all event categories with edit and delete options."""
    categories = Category.objects.order_by('name')
    return render(
        request,
        'events/category_list.html',
        {'categories': categories},
    )


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.'
            )

            return redirect('category_list')

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

            return redirect('category_list')

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
    """Allow admins to delete a category after confirmation."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category_name = category.name
        category.delete()

        messages.success(
            request,
            f'Category "{category_name}" deleted successfully.',
        )

        return redirect('category_list')

    return render(
        request,
        'events/category_confirm_delete.html',
        {'category': category},
    )
