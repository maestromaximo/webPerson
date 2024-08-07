import os
import re
import tempfile
from datetime import datetime
from PyPDF2 import PdfMerger
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from tqdm import tqdm
from education.models import Class, ClassBook, Lesson, Assignment, Notes
from education.utils import compile_latex_to_pdf_book

class Command(BaseCommand):
    help = 'Generate a comprehensive PDF book for all classes'

    def handle(self, *args, **kwargs):
        print('Starting the ClassBook generation process...')
        class_book = ClassBook.objects.create(
            name='Comprehensive ClassBook',
            slug=slugify('Comprehensive ClassBook')
        )
        print('ClassBook instance created.')

        with tempfile.TemporaryDirectory() as tempdir:
            pdf_paths = []

            for cls in tqdm(Class.objects.all(), desc="Processing classes"):
                print(f'Processing class: {cls.name}')
                class_pdf_path = os.path.join(tempdir, f"{slugify(cls.name)}.pdf")
                pdf_paths.append(class_pdf_path)
                self.generate_and_compile_class_pdf(cls, class_pdf_path, tempdir)

            final_pdf_path = os.path.join(tempdir, "final_classbook.pdf")
            self.merge_pdfs(pdf_paths, final_pdf_path)

            final_pdf_with_toc_path = os.path.join(tempdir, "final_classbook_with_toc.pdf")
            self.add_table_of_contents(pdf_paths, final_pdf_path, final_pdf_with_toc_path)

            with open(final_pdf_with_toc_path, 'rb') as final_pdf_file:
                class_book.pdf.save(f"classbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", ContentFile(final_pdf_file.read()))
                class_book.save()
                print('Successfully generated the ClassBook')

    def generate_and_compile_class_pdf(self, cls, output_path, tempdir):
        cover_page_latex = self.generate_class_cover_page(cls)
        cover_page_pdf = compile_latex_to_pdf_book(cover_page_latex)
        if cover_page_pdf is None:
            print(f"Failed to compile cover page for class: {cls.name}")
            return

        cover_page_path = os.path.join(tempdir, f"{slugify(cls.name)}_cover.pdf")
        with open(cover_page_path, 'wb') as cover_file:
            cover_file.write(cover_page_pdf)

        lesson_pdf_paths = []
        for lesson in tqdm(cls.lessons.all(), desc=f"Processing lessons for {cls.name}"):
            lesson_pdf_path = self.generate_and_compile_lesson_pdf(lesson, tempdir)
            if lesson_pdf_path:
                lesson_pdf_paths.append(lesson_pdf_path)

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
        summary = lesson.get_lecture_summary()
        print(f'Generating LaTeX for lesson: {lesson.title}')
        
        # Apply Markdown-like formatting to the summary
        formatted_summary = apply_markdown_to_latex(summary)
        
        latex_content = f"""
        \\documentclass{{article}}
        \\usepackage{{times}}
        \\usepackage{{amsmath}}
        \\usepackage{{amssymb}}
        \\usepackage{{enumitem}}
        \\usepackage{{hyperref}}
        \\usepackage{{geometry}}
        
        \\geometry{{
            a4paper,
            total={{170mm,257mm}},
            left=20mm,
            top=20mm,
        }}
        
        \\begin{{document}}
        \\section*{{{lesson.title}}}
        
        {formatted_summary}
        
        \\end{{document}}
        """
        
        print(f'LaTeX content for lesson {lesson.title}: {latex_content[:100]}...') # Print first 100 characters
        try:
            pdf_content = compile_latex_to_pdf_book(latex_content)
            if pdf_content is None:
                print(f'Failed to compile PDF for lesson: {lesson.title}')
                return None

            lesson_pdf_path = os.path.join(tempdir, f"{slugify(lesson.title)}.pdf")
            with open(lesson_pdf_path, 'wb') as lesson_pdf:
                lesson_pdf.write(pdf_content)
            return lesson_pdf_path
        except Exception as e:
            print(f'Exception occurred while compiling PDF for lesson: {lesson.title} - {str(e)}')
            return None
        
    def apply_markdown_to_latex(text):
        # Bold text
        text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
        
        # Inline math
        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
        
        # Display math
        text = re.sub(r'\\\[(.*?)\\\]', r'\\begin{equation*}\1\\end{equation*}', text)
        
        # Numbered lists
        text = re.sub(r'(\n\d+\.\s)', r'\n\\item ', text)
        text = re.sub(r'(^|\n)(\d+\.\s.*(\n|$))+', r'\n\\begin{enumerate}\n\g<0>\\end{enumerate}\n', text, flags=re.MULTILINE)
        
        # Bullet lists
        text = re.sub(r'(\n\s*-\s)', r'\n\\item ', text)
        text = re.sub(r'(^|\n)(\s*-\s.*(\n|$))+', r'\n\\begin{itemize}\n\g<0>\\end{itemize}\n', text, flags=re.MULTILINE)
        
        # Headers (assuming you want to use subsections for headers within lessons)
        text = re.sub(r'(?m)^#\s+(.*?)$', r'\\subsection*{\1}', text)
        text = re.sub(r'(?m)^##\s+(.*?)$', r'\\subsubsection*{\1}', text)
        
        # Code blocks (using verbatim environment)
        text = re.sub(r'```(.*?)```', r'\\begin{verbatim}\1\\end{verbatim}', text, flags=re.DOTALL)
        
        # Inline code
        text = re.sub(r'`(.*?)`', r'\\texttt{\1}', text)
        
        # Horizontal rule
        text = re.sub(r'---', r'\\hrulefill', text)
        
        # Links
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\\href{\2}{\1}', text)
        
        return text

    def get_assignment_pdf_paths(self, cls):
        pdf_paths = []
        for idx, assignment in enumerate(cls.assignments.all(), start=1):
            print(f'Processing assignment {idx} for class: {cls.name}')
            if assignment.pdf:
                pdf_paths.append(assignment.pdf.path)
            if assignment.answer_pdf:
                pdf_paths.append(assignment.answer_pdf.path)
        return pdf_paths

    def get_notes_pdf_paths(self, cls):
        pdf_paths = []
        for lesson in cls.lessons.all():
            for note in lesson.notes.all():
                print(f'Including note for lesson: {lesson.title}')
                pdf_paths.append(note.file.path)
        return pdf_paths

    def merge_pdfs(self, pdf_paths, output_path):
        merger = PdfMerger()
        for pdf_path in pdf_paths:
            print(f'Merging PDF: {pdf_path}')
            try:
                merger.append(pdf_path)
            except Exception as e:
                print(f"Error merging PDF {pdf_path}: {str(e)}")
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
        print('Compiling table of contents...')
        toc_pdf_content = compile_latex_to_pdf_book(toc_latex_content)
        if toc_pdf_content is None:
            print("Failed to compile table of contents")
            return

        toc_pdf_path = os.path.join(tempfile.gettempdir(), "table_of_contents.pdf")
        with open(toc_pdf_path, 'wb') as toc_pdf_file:
            toc_pdf_file.write(toc_pdf_content)

        print('Merging table of contents with the final PDF...')
        merger = PdfMerger()
        merger.append(toc_pdf_path)
        merger.append(input_pdf_path)
        merger.write(output_pdf_path)
        merger.close()