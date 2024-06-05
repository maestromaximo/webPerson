from django.core.management.base import BaseCommand
from education.models import Concept,Class,Lesson
from education.utils import create_concepts_from_lesson
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Create concepts from lessons in the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating concepts...'))
        all_classes = Class.objects.all()
        
        for c in tqdm(all_classes, desc="Processing Classes"):
            all_lessons = Lesson.objects.filter(related_class=c)
            for l in tqdm(all_lessons, desc=f"Processing Lessons for Class {c.name}", leave=False):
                if not Concept.objects.filter(related_lesson=l).exists():
                    val = create_concepts_from_lesson(l)
                    if val == 0:
                        self.stdout.write(self.style.ERROR("No concepts created for lesson: {}".format(l.title)))
                    
