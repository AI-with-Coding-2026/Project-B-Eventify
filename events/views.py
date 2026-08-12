from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import admin_required, organizer_required

from .forms import CategoryForm, EventForm
from .models import Category, Event


def event_list(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


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
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category created successfully.'
            )

            return redirect('category_create')

    else:
        form = CategoryForm()

    return render(
        request,
        'events/category_form.html',
        {
            'form': form,
            # Shared Create/Edit template labels
            'page_title': 'Create Category',
            'submit_label': 'Save Category',
        },
    )


# Admin can update/edit an existing category name & description
@admin_required
def category_update(request, pk):
    """Allow admins to edit an existing category name/description."""
    # Load the category by primary key, or return 404 if it does not exist
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        # instance=category makes this an update (not a create)
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Category updated successfully.'
            )

            # Redirect back to the same edit page after saving
            return redirect('category_update', pk=category.pk)

    else:
        # Prefill the form with the current category values
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
