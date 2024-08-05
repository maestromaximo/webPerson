import os
import tempfile
from datetime import datetime
from PyPDF2 import PdfMerger
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from tqdm import tqdm
from education.models import Class, ClassBook, StudySheet, Assignment
from education.utils import generate_study_guide as generate_study_guide_content, compile_latex_to_pdf

class Command(BaseCommand):
    help = 'Generate a comprehensive PDF book for all classes'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Starting to generate the ClassBook...'))

        # Create a new ClassBook
        class_book = ClassBook.objects.create(
            name='Comprehensive ClassBook',
            slug=slugify('Comprehensive ClassBook')
        )

        # Generate LaTeX content for the entire book
        self.stdout.write(self.style.NOTICE('Generating LaTeX content...'))
        latex_content, toc_content = self.generate_latex_content()
        
        # Combine the table of contents with the main content
        self.stdout.write(self.style.NOTICE('Combining LaTeX content...'))
        full_latex_content = r"\documentclass{book}"
        full_latex_content += r"\usepackage{times}"
        full_latex_content += r"\usepackage{pdfpages}"
        full_latex_content += r"\begin{document}"
        full_latex_content += r"\tableofcontents"
        full_latex_content += toc_content
        full_latex_content += latex_content
        full_latex_content += r"\end{document}"

        # Compile LaTeX content to PDF
        self.stdout.write(self.style.NOTICE('Compiling LaTeX to PDF...'))
        pdf_content = compile_latex_to_pdf(full_latex_content)
        
        if pdf_content:
            # Save the final PDF to the ClassBook model
            self.stdout.write(self.style.NOTICE('Saving the final PDF...'))
            class_book.pdf.save(f"classbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", ContentFile(pdf_content))
            class_book.save()
            self.stdout.write(self.style.SUCCESS('Successfully generated the ClassBook'))
        else:
            self.stdout.write(self.style.ERROR('Failed to generate the ClassBook PDF'))

    def generate_latex_content(self):
        latex_content = ""
        toc_content = ""

        classes = Class.objects.all()
        class_progress = tqdm(classes, desc="Processing Classes")

        for cls in class_progress:
            toc_content += r"\chapter{" + cls.name + "}\n"
            latex_content += r"\chapter{" + cls.name + "}\n"
            lessons = cls.lessons.all()
            lesson_progress = tqdm(lessons, desc=f"Processing Lessons for {cls.name}")

            for lesson in lesson_progress:
                toc_content += r"\section{" + lesson.title + "}\n"
                latex_content += r"\section{" + lesson.title + "}\n"
                latex_content += r"\subsection*{Summary}\n"
                latex_content += r"\begin{quote}\n"
                latex_content += lesson.get_lecture_summary()
                latex_content += r"\end{quote}\n"

                notes = lesson.notes.all()
                note_progress = tqdm(notes, desc=f"Processing Notes for {lesson.title}")

                for note in note_progress:
                    note_pdf_content = self.get_pdf_content(note.file.path)
                    if note_pdf_content:
                        latex_content += r"\includepdf[pages=-]{" + note.file.path.replace('\\', '/').replace('_', '\_') + "}\n"

            assignments = cls.assignments.all()
            assignment_progress = tqdm(assignments, desc=f"Processing Assignments for {cls.name}")

            for idx, assignment in enumerate(assignment_progress, start=1):
                toc_content += r"\section*{Assignment " + str(idx) + "}\n"
                latex_content += r"\section*{Assignment " + str(idx) + "}\n"
                if assignment.pdf:
                    latex_content += r"\includepdf[pages=-]{" + assignment.pdf.path.replace('\\', '/').replace('_', '\_') + "}\n"
                latex_content += r"\subsection*{Solutions}\n"
                if assignment.answer_pdf:
                    latex_content += r"\includepdf[pages=-]{" + assignment.answer_pdf.path.replace('\\', '/').replace('_', '\_') + "}\n"

        return latex_content, toc_content

    def get_pdf_content(self, file_path):
        try:
            with open(file_path, 'rb') as pdf_file:
                return pdf_file.read()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading PDF file {file_path}: {e}"))
            return None
