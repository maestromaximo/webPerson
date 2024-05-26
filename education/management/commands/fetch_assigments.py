import imaplib
import email
from email.header import decode_header
import os
import random
import tempfile
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
from education.models import Class, Assignment, AssigmentQuestion  # Adjust the import path as necessary
import fitz  # PyMuPDF
import cv2
import numpy as np
from education.utils import extract_pages_as_images, detect_question_marker, create_pdf_from_pages, cleanup_processed_files

CLASS_SLUGS = {
    'STAT333': 'stochastic-processes-333',
    'STAT231': 'statistics-231',
    'PHYS363': 'mechanics-363',
    'PHYS342': 'em2-342',
    'AMATH351': 'ordinary-differential-equations-351'
}

class Command(BaseCommand):
    help = 'Checks Gmail for unread emails with PDF attachments and processes them for assignments.'

    def handle(self, *args, **options):
        EMAIL_HOST_USER = settings.EMAIL_HOST_USER
        EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD
        print(f"Trying to log in with {EMAIL_HOST_USER} and provided password")

        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        try:
            mail.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS("Login successful"))

            mail.select("inbox")
            status, messages = mail.search(None, 'UNSEEN')
            if status != "OK":
                self.stdout.write(self.style.ERROR("No unread emails found."))
                return

            pdf_files = []
            for num in messages[0].split():
                status, msg_data = mail.fetch(num, '(RFC822)')
                if status != "OK":
                    self.stdout.write(self.style.ERROR(f"Failed to fetch email {num}."))
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        email_subject = decode_header(msg["subject"])[0][0]
                        email_from = decode_header(msg.get("From"))[0][0]
                        self.stdout.write(self.style.SUCCESS(f"Processing email from {email_from} with subject {email_subject}"))

                        if "assignment" in email_subject.lower():
                            for part in msg.walk():
                                if part.get_content_maintype() == 'multipart':
                                    continue
                                if part.get('Content-Disposition') is None:
                                    continue

                                file_name = part.get_filename()
                                if file_name:
                                    file_name, encoding = decode_header(file_name)[0]
                                    if isinstance(file_name, bytes):
                                        file_name = file_name.decode(encoding if encoding else 'utf-8')
                                    
                                if file_name and file_name.lower().endswith('.pdf'):
                                    file_path = os.path.join(settings.MEDIA_ROOT, 'assignments', file_name)
                                    with open(file_path, 'wb') as f:
                                        f.write(part.get_payload(decode=True))
                                    self.stdout.write(self.style.SUCCESS(f"Saved attachment {file_name}"))
                                    pdf_files.append(file_path)

                            mail.store(num, '+FLAGS', '\\Seen')
                        else:
                            self.stdout.write(self.style.WARNING(f"Ignoring email with subject: {email_subject}"))
                            mail.store(num, '-FLAGS', '(\Seen)')

            for pdf_path in pdf_files:
                pdf_name = os.path.basename(pdf_path)
                class_code = pdf_name.split()[0]
                class_slug = CLASS_SLUGS.get(class_code, None)

                self.stdout.write(self.style.SUCCESS(f"Processing PDF {pdf_name} for class code {class_code} with slug {class_slug}"))

                if class_slug:
                    related_class = Class.objects.filter(slug=class_slug).first()
                    if related_class:
                        self.stdout.write(self.style.SUCCESS(f"Found related class: {related_class}"))
                        lesson_page_indices = self.get_lesson_page_indices(pdf_path)
                        self.assign_pdfs_to_assignments(pdf_path, related_class, lesson_page_indices)
                    else:
                        self.stdout.write(self.style.WARNING(f"No related class found for slug: {class_slug}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No slug mapping found for class code: {class_code}"))

            mail.logout()
        except imaplib.IMAP4.error as e:
            self.stdout.write(self.style.ERROR(f"Login failed: {e}"))

    def get_lesson_page_indices(self, pdf_path):
        doc = fitz.open(pdf_path)
        lesson_page_indices = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            image_data = pix.tobytes("png")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img_file:
                temp_img_file.write(image_data)
                temp_img_file_path = temp_img_file.name

            if self.detect_black_circle(temp_img_file_path):
                lesson_page_indices.append(page_num)

            os.remove(temp_img_file_path)

        self.stdout.write(self.style.SUCCESS(f"Detected lesson page indices: {lesson_page_indices}"))
        return lesson_page_indices

    def detect_black_circle(self, image_path, square_size=(73, 45), threshold=0.05, debug=False):
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise ValueError(f"Image at {image_path} could not be loaded.")

        top_left_square = image[:square_size[1], :square_size[0]]
        blurred = cv2.GaussianBlur(top_left_square, (5, 5), 0)
        _, binary_image = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        processed_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)

        black_pixels = np.sum(processed_image == 0)
        total_pixels = processed_image.size
        proportion_black = black_pixels / total_pixels

        if debug:
            cv2.imshow('Processed Image', processed_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return proportion_black >= threshold

    def assign_pdfs_to_assignments(self, pdf_path, related_class, lesson_page_indices):
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        lesson_page_indices.append(num_pages)

        assignments = related_class.assignments.order_by('due_date')
        pdf_sections = []

        for i in range(len(lesson_page_indices) - 1):
            start_page = lesson_page_indices[i]
            end_page = lesson_page_indices[i + 1] - 1

            pdf_writer = fitz.open()
            for page_num in range(start_page, end_page + 1):
                pdf_writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
            section_pdf_path = os.path.join(settings.MEDIA_ROOT, 'assignments', f'{related_class.slug}_section_{i + 1}.pdf')
            pdf_writer.save(section_pdf_path)
            pdf_writer.close()

            pdf_sections.append(section_pdf_path)

        self.stdout.write(self.style.SUCCESS(f"Assignments found: {assignments.count()}"))
        self.stdout.write(self.style.SUCCESS(f"PDF sections created: {len(pdf_sections)}"))

        for assignment in assignments:
            if not assignment.answer_pdf:
                section_pdf_path = pdf_sections.pop(0) if pdf_sections else None
                if section_pdf_path:
                    random_suffix = str(random.randint(10000000, 99999999))
                    new_section_pdf_path = os.path.join('assignments', f'{related_class.slug}_section_{i + 1}_{random_suffix}.pdf')
                    os.rename(section_pdf_path, os.path.join(settings.MEDIA_ROOT, new_section_pdf_path))
                    assignment.answer_pdf = new_section_pdf_path
                    assignment.save()
                    self.stdout.write(self.style.SUCCESS(f"Assigned {new_section_pdf_path} to assignment {assignment.description}"))

                    if not assignment.questions.exists():
                        self.stdout.write(self.style.WARNING(f"No related questions for assignment {assignment.description}"))
                        self.break_down_pdf_and_create_questions(os.path.join(settings.MEDIA_ROOT, new_section_pdf_path), assignment)
            else:
                self.stdout.write(self.style.SUCCESS(f"Skipping assignment {assignment.description} because it already has an answer PDF."))

        if pdf_sections:
            self.stdout.write(self.style.WARNING(f"Unused PDF sections: {pdf_sections}"))

    def break_down_pdf_and_create_questions(self, pdf_path, assignment):
        pdf_reader = fitz.open(pdf_path)
        images = extract_pages_as_images(pdf_path)

        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed_pdfs')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        question_number = 1
        pages = []
        for i, image in enumerate(images):
            if detect_question_marker(image, i):
                if pages:
                    output_path = os.path.join(output_dir, f'Q{question_number}.pdf')
                    self.create_pdf_from_pages(pdf_reader, pages, output_path)
                    self.create_assignment_question(output_path, assignment, question_number)
                    question_number += 1
                pages = [i]
            else:
                pages.append(i)

        if pages:
            output_path = os.path.join(output_dir, f'Q{question_number}.pdf')
            self.create_pdf_from_pages(pdf_reader, pages, output_path)
            self.create_assignment_question(output_path, assignment, question_number)

    def create_pdf_from_pages(self, pdf_reader, pages, output_path):
        if not pages:
            print(f"No pages to create PDF for {output_path}")
            return
        
        pdf_writer = fitz.open()  # Corrected initialization
        print(f"Creating PDF: {output_path} with pages: {pages}")
        for page_num in pages:
            try:
                page = pdf_reader.load_page(page_num)  # Corrected way to access pages
                pdf_writer.insert_pdf(pdf_reader, from_page=page_num, to_page=page_num)
                print(f"Added page {page_num} to {output_path}")
            except Exception as e:
                print(f"Error adding page {page_num}: {e}")
        pdf_writer.save(output_path)
        print(f"Successfully created PDF: {output_path}")

    def create_assignment_question(self, pdf_path, assignment, question_number):
        random_suffix = str(random.randint(10000000, 99999999))
        final_pdf_path = os.path.join('assignments/answers/sectioned', f'Q{question_number}_{random_suffix}.pdf')
        os.rename(pdf_path, os.path.join(settings.MEDIA_ROOT, final_pdf_path))
        section_name = os.path.basename(final_pdf_path).replace('.pdf', '')

        question = AssigmentQuestion(
            section=section_name,
            answer=final_pdf_path,
            related_assignment=assignment
        )
        question.save()
        self.stdout.write(self.style.SUCCESS(f"Created AssigmentQuestion for {final_pdf_path} related to assignment {assignment.description}"))
