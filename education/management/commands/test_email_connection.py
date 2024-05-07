from django.core.management.base import BaseCommand
from django.conf import settings
import imaplib

class Command(BaseCommand):
    help = 'Tests IMAP login with the provided credentials'

    def handle(self, *args, **options):
        EMAIL_HOST_USER = settings.EMAIL_HOST_USER
        EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD
        self.stdout.write(f"email: {EMAIL_HOST_USER} password: {EMAIL_HOST_PASSWORD}")
        print(f"Trying to log in with {EMAIL_HOST_USER} and provided password")

        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        try:
            mail.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS("Login successful"))
            mail.logout()
        except imaplib.IMAP4.error as e:
            self.stdout.write(self.style.ERROR(f"Login failed: {e}"))
