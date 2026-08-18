from django.shortcuts import redirect, render

from .forms import StudentForm
from .models import Student


def student_list(request):
    students = Student.objects.all()

    if request.method == 'POST':
        form = StudentForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentForm()

    return render(
        request,
        'students/student_list.html',
        {
            'students': students,
            'form': form,
        },
    )