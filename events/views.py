from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import admin_required

from .forms import CategoryForm
from .models import Category, Event


def event_list(request):
    events = Event.objects.all().order_by('date')
    return render(request, 'events/event_list.html', {'events': events})


@admin_required
def category_list(request):
    """Display all event categories with edit and delete options."""
    categories = Category.objects.all()
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

            return redirect('category_list')

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
