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

from django import forms
from .models import Template, Lesson, Assignment

class TemplateSelectionForm(forms.Form):
    template = forms.ModelChoiceField(queryset=Template.objects.all(), label="Select Template")
    lessons = forms.ModelMultipleChoiceField(
        queryset=Lesson.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Lessons"
    )
    assignments = forms.ModelMultipleChoiceField(
        queryset=Assignment.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Assignments",
        required=False
    )

    def __init__(self, *args, **kwargs):
        class_instance = kwargs.pop('class_instance', None)
        super(TemplateSelectionForm, self).__init__(*args, **kwargs)
        if class_instance:
            self.fields['lessons'].queryset = Lesson.objects.filter(related_class=class_instance)
            self.fields['assignments'].queryset = Assignment.objects.filter(related_class=class_instance)
