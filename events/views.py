from django.contrib import messages
from django.shortcuts import redirect, render

from authentication.decorators import admin_required

from .forms import CategoryForm
from .models import Event


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