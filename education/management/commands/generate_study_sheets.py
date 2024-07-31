import os
from django.core.management.base import BaseCommand
from django.conf import settings
from education.models import Class, Lesson, StudySheet, Template
from education.views import generate_study_guide_content, compile_latex_to_pdf
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Generate study sheets for all classes, processing lessons in batches of four'

    def handle(self, *args, **options):
        classes = Class.objects.all()

        for class_instance in classes:
            lessons = class_instance.lessons.all()
            total_lessons = lessons.count()
            batch_size = 4
            batch_number = 1

            for i in range(0, total_lessons, batch_size):
                batch_lessons = lessons[i:i+batch_size]
                if not batch_lessons:
                    continue
                
                # Generate the study guide content (LaTeX)
                latex_code = generate_study_guide_content(template=Template.objects.filter().first() , class_instance=class_instance, lessons=batch_lessons)

                # Compile the LaTeX code into a PDF
                pdf_content = compile_latex_to_pdf(latex_code)
                if pdf_content:
                    study_sheet = StudySheet.objects.create(
                        class_belongs=class_instance,
                        title=f"Study Sheet {batch_number} for {class_instance.name}",
                        content=latex_code,
                        raw_latex=latex_code
                    )
                    study_sheet.pdf.save(f"study_sheet_{class_instance.slug}_{batch_number}.pdf", ContentFile(pdf_content))
                    study_sheet.save()
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to compile LaTeX for {class_instance.name} study sheet {batch_number}"))

                batch_number += 1

        self.stdout.write(self.style.SUCCESS('Successfully generated study sheets for all classes'))
