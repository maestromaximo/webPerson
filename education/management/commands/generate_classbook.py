import os
import tempfile
from datetime import datetime
from PyPDF2 import PdfMerger
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from education.models import Class, ClassBook
from education.utils import generate_study_guide as generate_study_guide_content, compile_latex_to_pdf

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

            # Generate LaTeX content and compile PDFs for each class
            for cls in Class.objects.all():
                self.stdout.write(self.style.NOTICE(f'Processing class: {cls.name}'))
                class_pdf_path = os.path.join(tempdir, f"{slugify(cls.name)}.pdf")
                pdf_paths.append(class_pdf_path)
                self.generate_and_compile_class_pdf(cls, class_pdf_path)

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

    def generate_and_compile_class_pdf(self, cls, output_path):
        latex_content = r"\documentclass{article}"
        latex_content += r"\usepackage{times}"
        latex_content += r"\usepackage{pdfpages}"
        latex_content += r"\begin{document}"

        latex_content += r"\section*{" + cls.name + "}\n"

        for lesson in cls.lessons.all():
            self.stdout.write(self.style.NOTICE(f'Processing lesson: {lesson.title}'))
            latex_content += r"\subsection*{" + lesson.title + "}\n"
            latex_content += r"\begin{quote}\n"
            latex_content += lesson.get_lecture_summary()
            latex_content += r"\end{quote}\n"

            for note in lesson.notes.all():
                self.stdout.write(self.style.NOTICE(f'Including note for lesson: {lesson.title}'))
                latex_content += r"\includepdf[pages=-]{" + note.file.path.replace('\\', '/').replace('_', '\_') + "}\n"

        for idx, assignment in enumerate(cls.assignments.all(), start=1):
            self.stdout.write(self.style.NOTICE(f'Processing assignment {idx} for class: {cls.name}'))
            latex_content += r"\subsection*{Assignment " + str(idx) + "}\n"
            if assignment.pdf:
                latex_content += r"\includepdf[pages=-]{" + assignment.pdf.path.replace('\\', '/').replace('_', '\_') + "}\n"
            latex_content += r"\subsubsection*{Solutions}\n"
            if assignment.answer_pdf:
                latex_content += r"\includepdf[pages=-]{" + assignment.answer_pdf.path.replace('\\', '/').replace('_', '\_') + "}\n"

        latex_content += r"\end{document}"

        # Compile LaTeX content to PDF
        pdf_content = compile_latex_to_pdf(latex_content)

        # Save the compiled PDF to the specified output path
        if pdf_content:
            with open(output_path, 'wb') as pdf_file:
                pdf_file.write(pdf_content)
            self.stdout.write(self.style.SUCCESS(f'Successfully compiled PDF for class: {cls.name}'))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to compile PDF for class: {cls.name}'))

    def merge_pdfs(self, pdf_paths, output_path):
        merger = PdfMerger()
        for pdf_path in pdf_paths:
            merger.append(pdf_path)
        merger.write(output_path)
        merger.close()

    def add_table_of_contents(self, pdf_paths, input_pdf_path, output_pdf_path):
        toc_latex_content = r"\documentclass{book}"
        toc_latex_content += r"\usepackage{times}"
        toc_latex_content += r"\usepackage{pdfpages}"
        toc_latex_content += r"\begin{document}"
        toc_latex_content += r"\tableofcontents"
        toc_latex_content += r"\end{document}"

        toc_pdf_content = compile_latex_to_pdf(toc_latex_content)
        toc_pdf_path = os.path.join(tempfile.gettempdir(), "table_of_contents.pdf")
        with open(toc_pdf_path, 'wb') as toc_pdf_file:
            toc_pdf_file.write(toc_pdf_content)

        merger = PdfMerger()
        merger.append(toc_pdf_path)
        merger.append(input_pdf_path)
        merger.write(output_pdf_path)
        merger.close()
