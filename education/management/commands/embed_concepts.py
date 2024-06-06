from django.core.management.base import BaseCommand
from education.models import Concept,Class,Lesson
from education.utils import create_concepts_from_lesson
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Embed concepts for concepts in the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Embedding concepts...'))
        concepts = Concept.objects.all()
        for c in tqdm(concepts, desc="Processing Concepts"):
            c.embed()
            c.save()
        self.stdout.write(self.style.SUCCESS('Concepts embedded successfully.'))

