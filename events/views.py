from django.contrib import messages
from django.shortcuts import redirect, render

from authentication.decorators import admin_required

from .forms import CategoryForm
from .models import Event


def event_list(request):
    events = Event.objects.all().order_by('date')

    # Filtre par catégorie
    category = request.GET.get('category')
    if category:
        events = events.filter(category=category)

    # Filtre par recherche (titre)
    search = request.GET.get('search')
    if search:
        events = events.filter(title__icontains=search)

    # Filtre par prix max
    max_price = request.GET.get('max_price')
    if max_price:
        events = events.filter(price__lte=max_price)

    context = {
        'events': events,
        'categories': Event.CATEGORY_CHOICES,
        'selected_category': category,
        'search_query': search or '',
        'max_price': max_price or '',
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