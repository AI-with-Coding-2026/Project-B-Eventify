from django.shortcuts import get_object_or_404, redirect, render

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


def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)

    return render(
        request,
        'students/student_detail.html',
        {
            'student': student,
        },
    )


def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)

        if form.is_valid():
            form.save()
            return redirect('student_detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)

    return render(
        request,
        'students/student_edit.html',
        {
            'form': form,
            'student': student,
        },
    )


def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        student.delete()
        return redirect('student_list')

    return render(
        request,
        'students/student_confirm_delete.html',
        {
            'student': student,
        },
    )