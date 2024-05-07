from django.core.management.base import BaseCommand
from django.conf import settings
import imaplib
import email
from email.header import decode_header
from education.models import Notes
import os


class Command(BaseCommand):
    help = 'Fetches notes from a designated email account'

    def handle(self, *args, **options):
        self.stdout.write("Fetching new notes...")
        self.fetch_notes()

    def fetch_notes(self):
        
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        imap.select("inbox")

        status, messages = imap.search(None, 'UNSEEN')
        if status != 'OK':
            self.stdout.write("No new emails found.")
            return

        for num in messages[0].split():
            typ, data = imap.fetch(num, '(RFC822)')
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg["subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    self.stdout.write(f"Processing {subject}...")

                    for part in msg.walk():
                        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                            continue
                        filename = part.get_filename()

                        if filename and filename.endswith('.pdf'):
                            # Write the file to the media directory
                            filepath = os.path.join(settings.MEDIA_ROOT, 'notes', filename)
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            with open(filepath, 'wb') as fp:
                                fp.write(part.get_payload(decode=True))
                            
                            # Use get_or_create to avoid duplicate entries, update if exists
                            note, created = Notes.objects.get_or_create(name=subject, defaults={'file': filename})
                            if not created:
                                note.file = filename  # Update the file path if note already exists
                                note.save()
                            self.stdout.write(f"{'Created' if created else 'Updated'} note for {subject}.")
        imap.close()
        imap.logout()
