import os
import tempfile
from datetime import datetime
from PyPDF2 import PdfMerger
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from tqdm import tqdm
from education.models import Class, ClassBook, Lesson, Assignment, Notes
from education.utils import compile_latex_to_pdf

class Command(BaseCommand):
    help = 'Generate a comprehensive PDF book for all classes'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Starting the ClassBook generation process...'))
        # Create a new ClassBook
        class_book = ClassBook.objects.create(
            name='Comprehensive ClassBook',
            slug=slugify('Comprehensive ClassBook')
        )
        self.stdout.write(self.style.NOTICE('ClassBook instance created.'))

        # Temporary directory to store individual PDFs
        with tempfile.TemporaryDirectory() as tempdir:
            pdf_paths = []

            # Generate and compile PDFs for each class
            for cls in tqdm(Class.objects.all(), desc="Processing classes"):
                self.stdout.write(self.style.NOTICE(f'Processing class: {cls.name}'))
                class_pdf_path = os.path.join(tempdir, f"{slugify(cls.name)}.pdf")
                pdf_paths.append(class_pdf_path)
                self.generate_and_compile_class_pdf(cls, class_pdf_path, tempdir)

            # Merge all class PDFs into one final PDF
            final_pdf_path = os.path.join(tempdir, "final_classbook.pdf")
            self.merge_pdfs(pdf_paths, final_pdf_path)

            # Add table of contents to the final PDF
            final_pdf_with_toc_path = os.path.join(tempdir, "final_classbook_with_toc.pdf")
            self.add_table_of_contents(pdf_paths, final_pdf_path, final_pdf_with_toc_path)

            # Save the final PDF to the ClassBook model
            with open(final_pdf_with_toc_path, 'rb') as final_pdf_file:
                class_book.pdf.save(f"classbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", ContentFile(final_pdf_file.read()))
                class_book.save()
                self.stdout.write(self.style.SUCCESS('Successfully generated the ClassBook'))

    def generate_and_compile_class_pdf(self, cls, output_path, tempdir):
        # Create a cover page for the class
        cover_page_latex = self.generate_class_cover_page(cls)
        cover_page_pdf = compile_latex_to_pdf(cover_page_latex)
        cover_page_path = os.path.join(tempdir, f"{slugify(cls.name)}_cover.pdf")
        with open(cover_page_path, 'wb') as cover_file:
            cover_file.write(cover_page_pdf)

        # Generate PDFs for each lesson
        lesson_pdf_paths = []
        for lesson in tqdm(cls.lessons.all(), desc=f"Processing lessons for {cls.name}"):
            lesson_pdf_path = self.generate_and_compile_lesson_pdf(lesson, tempdir)
            lesson_pdf_paths.append(lesson_pdf_path)

        # Merge cover page, lessons, notes, and assignments into a single class PDF
        class_pdf_paths = [cover_page_path] + lesson_pdf_paths + self.get_assignment_pdf_paths(cls) + self.get_notes_pdf_paths(cls)
        self.merge_pdfs(class_pdf_paths, output_path)

    def generate_class_cover_page(self, cls):
        return f"""
        \\documentclass{{article}}
        \\usepackage{{times}}
        \\begin{{document}}
        \\begin{{center}}
        \\LARGE \\textbf{{{cls.name}}} \\\\
        \\end{{center}}
        \\end{{document}}
        """

    def generate_and_compile_lesson_pdf(self, lesson, tempdir):
        # latex_content = f"""
        # \\documentclass{{article}}
        # \\usepackage{{times}}
        # \\begin{{document}}
        # \\section*{{{lesson.title}}}
        # \\begin{{quote}}
        # {lesson.get_lecture_summary()}
        # \\end{{quote}}
        # \\end{{document}}
        # """
        latex_content = f"""
        \\documentclass{{article}}
        \\usepackage{{times}}
        \\begin{{document}}
        \\section*{{{lesson.title}}}
        \\end{{document}}
        """
        print("debugging latex_content in") 

        pdf_content = compile_latex_to_pdf(latex_content)
        lesson_pdf_path = os.path.join(tempdir, f"{slugify(lesson.title)}.pdf")
        with open(lesson_pdf_path, 'wb') as lesson_pdf:
            lesson_pdf.write(pdf_content)
        return lesson_pdf_path

    def get_assignment_pdf_paths(self, cls):
        pdf_paths = []
        for idx, assignment in enumerate(cls.assignments.all(), start=1):
            self.stdout.write(self.style.NOTICE(f'Processing assignment {idx} for class: {cls.name}'))
            if assignment.pdf:
                pdf_paths.append(assignment.pdf.path.replace('\\', '/').replace('_', '\_'))
            if assignment.answer_pdf:
                pdf_paths.append(assignment.answer_pdf.path.replace('\\', '/').replace('_', '\_'))
        return pdf_paths

    def get_notes_pdf_paths(self, cls):
        pdf_paths = []
        for lesson in cls.lessons.all():
            for note in lesson.notes.all():
                self.stdout.write(self.style.NOTICE(f'Including note for lesson: {lesson.title}'))
                pdf_paths.append(note.file.path.replace('\\', '/').replace('_', '\_'))
        return pdf_paths

    def merge_pdfs(self, pdf_paths, output_path):
        merger = PdfMerger()
        for pdf_path in pdf_paths:
            self.stdout.write(self.style.NOTICE(f'Merging PDF: {pdf_path}'))
            merger.append(pdf_path)
        merger.write(output_path)
        merger.close()

    def add_table_of_contents(self, pdf_paths, input_pdf_path, output_pdf_path):
        toc_latex_content = r"""
        \documentclass{book}
        \usepackage{times}
        \usepackage{pdfpages}
        \begin{document}
        \tableofcontents
        \end{document}
        """
        self.stdout.write(self.style.NOTICE('Compiling table of contents...'))
        toc_pdf_content = compile_latex_to_pdf(toc_latex_content)
        toc_pdf_path = os.path.join(tempfile.gettempdir(), "table_of_contents.pdf")
        with open(toc_pdf_path, 'wb') as toc_pdf_file:
            toc_pdf_file.write(toc_pdf_content)

        self.stdout.write(self.style.NOTICE('Merging table of contents with the final PDF...'))
        merger = PdfMerger()
        merger.append(toc_pdf_path)
        merger.append(input_pdf_path)
        merger.write(output_pdf_path)
        merger.close()
