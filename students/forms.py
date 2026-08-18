from django import forms

from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'favourite_subject', 'birth_date']
        widgets = {
            'birth_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
        }