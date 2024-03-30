from django.db import models
from django.utils.text import slugify

# Enum choices for later use
PROBLEM_TYPE_CHOICES = [
    ('Fixed Answer', 'Fixed Answer'),
    ('Variable Answer', 'Variable Answer'),
]

ANSWER_TYPE_CHOICES = [
    ('Number', 'Number'),
    ('Text', 'Text'),
    ('Vector', 'Vector'),
]

# Define enum choices where necessary
SOURCE_CHOICES = [
    ('Lecture', 'Lecture'),
    ('Student', 'Student'),
]

PROMPT_CHOICES = [
    ('Insight', 'Insight'),
    ('Technical', 'Technical'),
    ('Creative', 'Creative'),
    ('Other', 'Other'),
]

class Class(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    slug = models.SlugField(null=True, blank=True)  # For SEO-friendly URLs
    # Link to a Book will be defined in the Book model as a OneToOneField

    def __str__(self):
        return f"{self.name} ({self.subject})"
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)  # Slugify the name
        super().save(*args, **kwargs)
    


class Schedule(models.Model):
    class_belongs = models.ForeignKey(Class, related_name='schedules', on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=9)  # e.g., "Monday", "Tuesday", etc.
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.class_belongs.name} - {self.day_of_week} {self.start_time} to {self.end_time}"

class Book(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(null=True, blank=True)
    pdf = models.FileField(upload_to='books/')
    index_contents = models.TextField(null=True, blank=True)
    page_count = models.IntegerField()
    related_class = models.OneToOneField(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='book')

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Lesson(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    related_class = models.ForeignKey(Class, related_name='lessons', on_delete=models.CASCADE)
    slug = models.SlugField(null=True, blank=True)

    def __str__(self):
        return f"{self.title or 'Unnamed Lesson'} - {self.related_class.name}"
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Problem(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    steps = models.TextField(null=True, blank=True)
    solution = models.TextField()
    problem_type = models.CharField(max_length=50, choices=PROBLEM_TYPE_CHOICES)
    answer_type = models.CharField(max_length=50, choices=ANSWER_TYPE_CHOICES)
    related_lessons = models.ManyToManyField(Lesson, related_name='problems')

    def __str__(self):
        return self.description[:50]  # Show first 50 chars
    
class Tool(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    path = models.FilePathField(null=True, blank = True, help_text="Path to the tool")
    code = models.TextField()
    schema = models.JSONField()
    description = models.TextField(null=True, blank=True)
    associated_problem = models.ForeignKey(Problem, null=True, related_name='tools', on_delete=models.CASCADE)

class Transcript(models.Model):
    content = models.TextField()
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    related_lesson = models.ForeignKey(Lesson, related_name='transcripts', on_delete=models.CASCADE)

class Notes(models.Model):
    file = models.FileField(upload_to='notes/')
    text_summary = models.TextField(null=True, blank=True)
    related_lesson = models.ForeignKey(Lesson, related_name='notes', on_delete=models.CASCADE)


class Assignment(models.Model):
    description = models.TextField(null=True, blank=True)
    due_date = models.DateTimeField()
    related_class = models.ForeignKey(Class, related_name='assignments', on_delete=models.CASCADE)
    pdf = models.FileField(upload_to='assignments/', null=True, blank=True)

    def __str__(self):
        return f"{self.related_class.name} assignment due {self.due_date}"

class ProblemSet(models.Model):
    related_lessons = models.ManyToManyField(Lesson)

    def __str__(self):
        return f"Problem Set for {'; '.join(lesson.title for lesson in self.related_lessons.all())}"

class Test(models.Model):
    related_class = models.ForeignKey(Class, related_name='tests', on_delete=models.CASCADE)
    content_area = models.TextField()
    date = models.DateTimeField()
    duration = models.IntegerField()  # Duration in minutes

    def __str__(self):
        return f"{self.related_class.name} Test on {self.date}"

class Prompt(models.Model):
    title = models.CharField(max_length=255)
    prompt = models.TextField()
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, choices=PROMPT_CHOICES, default='Other')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def format_prompt(self, *args, **kwargs):
        """
        Formats the prompt string with the provided arguments using Python's str.format() method.
        This allows for dynamic insertion of values into the prompt template.

        :param args: Positional arguments for placeholders.
        :param kwargs: Keyword arguments for named placeholders.
        :return: A formatted prompt string.
        """
        return self.prompt.format(*args, **kwargs)

    @classmethod
    def filter_by_category(cls, category):
        """
        Filters prompts by category.

        :param category: The category to filter by.
        :return: QuerySet of prompts that match the category.
        """
        return cls.objects.filter(category=category, active=True)
    
class GPTInstance(models.Model):
    model_name = models.CharField(max_length=70)
    slug = models.SlugField(max_length=70, unique=True)
    tools = models.ManyToManyField(Tool, blank=True)
    use_embeddings = models.BooleanField(default=False)
    web_access = models.BooleanField(default=False)
    pre_feed_context = models.JSONField(blank=True, null=True)
    default_path = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=50, default='gpt-3.5-turbo-0613')

    def __str__(self):
        return self.model_name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def no_context_chat(self, prompt):
        # Placeholder for no context chat method
        pass

    def chat(self, prompt, conversation=None):
        # Placeholder for chat method with optional conversation context
        pass

    def execute_tool(self, prompt, tool):
        # Placeholder for tool execution method
        pass

class Conversation(models.Model):
    gpt_instance = models.ForeignKey(GPTInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    title = models.CharField(max_length=120, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Conversation {self.id}"

    def set_title(self):
        # Placeholder method to set conversation title based on messages
        pass

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    is_user_message = models.BooleanField(default=True)  # True if from user, False if from AI
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.id} - {('User' if self.is_user_message else 'assistant')} - {self.text[:50]}"
