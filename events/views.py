from django.shortcuts import get_object_or_404, render

from .models import Event


def event_list(request):
    events = Event.objects.all().order_by('date')

    return render(
        request,
        'events/event_list.html',
        {
            'events': events,
        },
    )


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    return render(
        request,
        'events/event_detail.html',
        {
            'event': event,
        },
    )