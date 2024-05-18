import imaplib
import email
from email.header import decode_header
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
from education.models import Notes, Class, Lesson  # Adjust the import path as necessary
import fitz  # PyMuPDF
import cv2
import numpy as np

class Command(BaseCommand):
    help = 'Checks Gmail for unread emails with PDF attachments and creates Notes objects.'

    def handle(self, *args, **options):
        EMAIL_HOST_USER = settings.EMAIL_HOST_USER
        EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD
        self.stdout.write(f"email: {EMAIL_HOST_USER} password: {EMAIL_HOST_PASSWORD}")
        print(f"Trying to log in with {EMAIL_HOST_USER} and provided password")

        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        try:
            mail.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS("Login successful"))

            # Select the mailbox you want to check
            mail.select("inbox")

            # Search for all unread emails
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
                        # Get the email content
                        email_subject = decode_header(msg["subject"])[0][0]
                        email_from = decode_header(msg.get("From"))[0][0]
                        self.stdout.write(self.style.SUCCESS(f"Processing email from {email_from} with subject {email_subject}"))

                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue

                            file_name = part.get_filename()
                            if file_name and file_name.lower().endswith('.pdf'):
                                file_path = os.path.join(settings.MEDIA_ROOT, 'notes', file_name)
                                with open(file_path, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                                self.stdout.write(self.style.SUCCESS(f"Saved attachment {file_name}"))
                                pdf_files.append(file_path)

            # Process each saved PDF
            for pdf_path in pdf_files:
                pdf_name = os.path.basename(pdf_path)
                class_slug = pdf_name.split('.')[0]  # Assuming the file name format is class_slug.pdf
                related_class = Class.objects.filter(slug=class_slug).first()
                if related_class:
                    lesson_page_indices = self.get_lesson_page_indices(pdf_path)
                    self.create_notes_from_pdf(pdf_path, related_class, lesson_page_indices)

            mail.logout()
        except imaplib.IMAP4.error as e:
            self.stdout.write(self.style.ERROR(f"Login failed: {e}"))

    def get_lesson_page_indices(self, pdf_path):
        """Extracts the page indices for each lesson based on the black circle marker."""
        doc = fitz.open(pdf_path)
        lesson_page_indices = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            image_data = pix.samples  # You can use an image processing library to analyze this image data
            if self.detect_black_circle(image_data):
                lesson_page_indices.append(page_num)
        return lesson_page_indices

    def detect_black_circle(image_path, square_size=(100, 100), threshold=0.1):
        """
        Detects a black circle in the top left of the page.

        Parameters:
        - image_path: Path to the image file.
        - square_size: Tuple indicating the size of the square to check (width, height).
        - threshold: Proportion of black pixels required to consider the circle detected.

        Returns:
        - Boolean indicating whether the circle is detected.
        """
        # Load the image
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise ValueError(f"Image at {image_path} could not be loaded.")

        # Define the area to check (top-left corner)
        top_left_square = image[:square_size[1], :square_size[0]]

        # Apply Gaussian blur to smooth the image
        blurred = cv2.GaussianBlur(top_left_square, (5, 5), 0)

        # Threshold the image to get a binary image (everything that is not pure white becomes black)
        _, binary_image = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY)

        # Apply morphological operations to fill in gaps
        kernel = np.ones((5, 5), np.uint8)
        processed_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)

        # Calculate the proportion of black pixels
        black_pixels = np.sum(processed_image == 0)
        total_pixels = processed_image.size
        proportion_black = black_pixels / total_pixels

        return proportion_black >= threshold

    def create_notes_from_pdf(self, pdf_path, related_class, lesson_page_indices):
        """Creates Notes objects from the PDF based on the lesson page indices."""
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        lesson_page_indices.append(num_pages)  # Add the end of the document as the last index for slicing

        lessons = related_class.lessons.order_by('id')
        for i in range(len(lesson_page_indices) - 1):
            start_page = lesson_page_indices[i]
            end_page = lesson_page_indices[i + 1] - 1

            pdf_writer = fitz.open()
            for page_num in range(start_page, end_page + 1):
                pdf_writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
            section_pdf_path = os.path.join(settings.MEDIA_ROOT, 'notes', f'{related_class.slug}_section_{i + 1}.pdf')
            pdf_writer.save(section_pdf_path)
            pdf_writer.close()

            lesson = lessons[i] if i < len(lessons) else None
            if lesson and not lesson.notes.exists():
                note_name = slugify(f'{related_class.slug}_section_{i + 1}')
                note = Notes(name=note_name, file=f'notes/{related_class.slug}_section_{i + 1}.pdf', related_lesson=lesson)
                note.save()
                self.stdout.write(self.style.SUCCESS(f"Created Notes object for {section_pdf_path} related to lesson {lesson.title}"))

