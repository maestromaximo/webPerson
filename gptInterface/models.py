from django.db import models
from django.utils.text import slugify

# Create your models here.
class ChatModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    notes = models.TextField(blank=True)
    model_name = models.CharField(max_length=50, default='gpt-3.5-turbo-0613')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If the slug is not set, generate it from the name
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure the slug is unique and append a number if it's not
            original_slug = self.slug
            counter = 1
            while ChatModel.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)
