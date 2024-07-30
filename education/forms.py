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


from .models import Template, Lesson, Assignment

class TemplateSelectionForm(forms.Form):
    template = forms.ModelChoiceField(queryset=Template.objects.all(), label="Select Template")
    lessons = forms.ModelMultipleChoiceField(queryset=Lesson.objects.all(), widget=forms.CheckboxSelectMultiple, label="Select Lessons")
    assignments = forms.ModelMultipleChoiceField(queryset=Assignment.objects.all(), widget=forms.CheckboxSelectMultiple, label="Select Assignments", required=False)
