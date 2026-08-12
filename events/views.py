from django.contrib import messages
from django.shortcuts import redirect, render

from authentication.decorators import admin_required, attendee_required
from django.shortcuts import get_object_or_404

from .forms import BookingForm
from authentication.models import User

from .forms import CategoryForm
from .models import Event
from .models import Booking


def event_list(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


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
        {'form': form}
    )


@attendee_required
def book_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            Booking = getattr(event.__class__.__module__ and __import__(event.__class__.__module__, fromlist=['Booking']), 'Booking', None)
            # create booking record
            # to avoid circular imports we use the Booking model from events.models
            Booking.objects.create(
                event=event,
                user_id=request.user.id,
                quantity=quantity,
            )

            messages.success(request, 'Booking successful.')
            return redirect('event_list')
    else:
        form = BookingForm()

    return render(request, 'events/book.html', {'event': event, 'form': form})


@attendee_required
def my_bookings(request):
    bookings = Booking.objects.filter(user_id=request.user.id).select_related('event')
    return render(request, 'events/my_bookings.html', {'bookings': bookings})