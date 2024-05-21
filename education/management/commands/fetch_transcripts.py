import os
import json
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from education.models import Lesson, Class, Transcript
from education.utils import transcribe_audio_local as transcribe_audio
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

# Constants
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SCOPES = [os.getenv('SCOPES')]
DESTINATION_FOLDER = os.getenv('DESTINATION_FOLDER')
RECORDINGS_JSON_FILE = os.getenv('RECORDINGS_JSON_FILE')
SEARCH_TERMS = ["STAT333", "STAT231", "PHYS363", "PHYS342", "AMATH351"]

CLASS_SLUGS = {
    'STAT333': 'stochastic-processes-333',
    'STAT231': 'statistics-231',
    'PHYS363': 'mechanics-363',
    'PHYS342': 'em2-342',
    'AMATH351': 'ordinary-differential-equations-351'
}

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Drive service
service = build('drive', 'v3', credentials=credentials)

def search_files(service, query):
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        return items
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def download_file(service, file_id, file_name, destination_folder):
    request = service.files().get_media(fileId=file_id)
    file_path = os.path.join(destination_folder, file_name)

    with open(file_path, 'wb') as file:
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f'Download {int(status.progress() * 100)}%.')
    return file_path

class Command(BaseCommand):
    help = 'Download and process recordings from Google Drive'

    def handle(self, *args, **kwargs):
        # Ensure destination folder exists
        if not os.path.exists(DESTINATION_FOLDER):
            os.makedirs(DESTINATION_FOLDER)

        # Load or initialize recordings list
        if os.path.exists(RECORDINGS_JSON_FILE):
            with open(RECORDINGS_JSON_FILE, 'r') as f:
                recordings = json.load(f)
        else:
            recordings = {}

        found_files = {}
        for term in SEARCH_TERMS:
            search_query = f"name contains '{term}'"
            files = search_files(service, search_query)
            if files:
                for file in files:
                    found_files[file['id']] = file['name']
        
        # Remove already recorded files from found_files
        new_files = {file_id: name for file_id, name in found_files.items() if file_id not in recordings}

        # Update the recordings list with new files
        recordings.update(new_files)

        # Save the updated recordings list
        with open(RECORDINGS_JSON_FILE, 'w') as f:
            json.dump(recordings, f, indent=4)

        # Process and download new files
        for file_id, name in tqdm(sorted(new_files.items(), key=lambda x: x[1]), desc="Processing files"):
            print(f"Found new file: {name} (ID: {file_id})")
            file_path = download_file(service, file_id, name, DESTINATION_FOLDER)
            print(f"Downloaded {name} to {DESTINATION_FOLDER}")

            # Process the downloaded file
            try:
                transcript_text = transcribe_audio(file_path)

                # Determine the class and related lesson
                class_slug_key = next((key for key in CLASS_SLUGS.keys() if key in name), None)
                if not class_slug_key:
                    print(f"Class slug not found for file: {name}")
                    continue
                
                related_class = get_object_or_404(Class, slug=CLASS_SLUGS[class_slug_key])
                lesson_count = related_class.lessons.count()
                lesson_title = f"{related_class.name} Lesson {lesson_count + 1}"

                # Create the lesson
                lesson = Lesson.objects.create(
                    title=lesson_title,
                    related_class=related_class,
                    slug=slugify(lesson_title)
                )

                # Determine the source of the transcript
                source = 'Student' if ' s ' in name or ' s.' in name or name.endswith(' s') else 'Lecture'

                # Create the transcript
                Transcript.objects.create(
                    content=transcript_text,
                    source=source,
                    related_lesson=lesson
                )

                # Save the lesson
                lesson.save()
                print(f"Processed and saved lesson: {lesson.title}")

                # Delete the downloaded file
                os.remove(file_path)

            except Exception as e:
                print(f"Error processing file {name}: {e}")

if __name__ == '__main__':
    Command().handle()
