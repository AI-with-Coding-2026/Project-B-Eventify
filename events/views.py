from django.contrib import messages
from django.shortcuts import redirect, render

from authentication.decorators import admin_required

from .forms import CategoryForm
from .models import Event


def event_list(request):
    events = Event.objects.all().order_by('date')

    search_query = request.GET.get('search', '')
    selected_category = request.GET.get('category', '')
    max_price = request.GET.get('max_price', '')

    if search_query:
        events = events.filter(title__icontains=search_query)

    if selected_category:
        events = events.filter(category=selected_category)

    if max_price:
        events = events.filter(price__lte=max_price)

    context = {
        'events': events,
        'categories': Event.CATEGORY_CHOICES,
        'search_query': search_query,
        'selected_category': selected_category,
        'max_price': max_price,
    }
    return render(request, 'events/event_list.html', context)


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