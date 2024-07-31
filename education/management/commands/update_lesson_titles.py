import json
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from education.models import Lesson  # Update with your actual app name
from education.utils import interact_with_gpt
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Update lesson titles and slugs based on the summarized lecture transcript'

    def handle(self, *args, **options):
        lessons = Lesson.objects.all()
        total_lessons = lessons.count()
        
        with tqdm(total=total_lessons, desc="Updating lessons") as pbar:
            for lesson in lessons:
                # Get the lecture summary
                lecture_summary = lesson.get_lecture_summary()
                if lecture_summary == "no summary available":
                    self.stdout.write(self.style.WARNING(f"No summary available for lesson ID {lesson.id}"))
                    pbar.update(1)
                    continue

                # Generate a new lesson title using GPT
                class_name = lesson.related_class.name
                prompt = f'Here is a lesson summary from the "{class_name}", please provide an accurate lesson title in JSON format like this: {{"title": "The representative lesson title"}}\nLesson summary: {lecture_summary}'
                response = interact_with_gpt(lecture_summary, prompt, use_gpt4=False)

                try:
                    # Parse the JSON response to get the new title
                    new_title = json.loads(response)["title"]
                except (json.JSONDecodeError, KeyError) as e:
                    self.stdout.write(self.style.ERROR(f"Error parsing GPT response for lesson ID {lesson.id}: {e}"))
                    pbar.update(1)
                    continue

                # Update the lesson title and slug
                lesson.title = new_title
                lesson.slug = slugify(new_title)
                lesson.save()

                self.stdout.write(self.style.SUCCESS(f"Updated lesson ID {lesson.id}: {new_title}"))
                pbar.update(1)
