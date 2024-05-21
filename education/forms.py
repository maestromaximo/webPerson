from django import forms
from .models import Lesson

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title']  # Assuming you have a file field for the lesson

class TranscriptionUploadForm(forms.Form):
    lecture_file = forms.FileField(required=False, label="Upload Lecture Audio")
    student_file = forms.FileField(required=False, label="Upload Student Audio")


class UploadPDFForm(forms.Form):
    pdf = forms.FileField()
