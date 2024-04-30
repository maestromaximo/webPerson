import os
import re
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from PyPDF2 import PdfReader
import pdfplumber
from .utils import extract_toc_text, extract_toc_until_page, find_first_toc_page, parse_toc

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
    index_contents = models.JSONField(null=True, blank=True)
    page_count = models.IntegerField()
    related_class = models.OneToOneField(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='book')
    page_offset = models.IntegerField(default=0, help_text="The page number of the first page in the book from where the page count starts, for example page 1 could start counting on the physical page 7, after the preface.")
   
    
    def update_index_from_pdf(self, skip_from_page=2, continuous=True):
        """Updates the index_contents field by extracting and parsing the ToC from the PDF."""
        pdf_path = os.path.join(settings.MEDIA_ROOT, self.pdf.name)
        toc_dict = find_first_toc_page(pdf_path, skip_from_page=skip_from_page, continuous=continuous)
        if toc_dict:
            self.index_contents = str(toc_dict)
        else:
            self.index_contents = {}


    # def extract_footer_text(self, pdf_path, page_number):
    #     """Extract text from the footer of a specific page of the PDF file."""
    #     with open(pdf_path, "rb") as file:
    #         reader = PdfReader(file)
    #         if page_number < len(reader.pages):
    #             page = reader.pages[page_number]
    #             # Define the footer area (may need to adjust coordinates)
    #             # For PyPDF2, this will adjust the crop box to only include the bottom part of the page
    #             media_box = page.mediabox
    #             footer_height = media_box[3] * 0.2  # Adjust the 0.2 if necessary for footer height
    #             page.cropbox.lower_left = (media_box[0], media_box[1])
    #             page.cropbox.upper_right = (media_box[2], media_box[1] + footer_height)
    #             return page.extract_text()
    #         else:
    #             return None
    def extract_footer_text(self, pdf_path, page_number, footer_height=0.09):
        """Extract text from the footer of a specific page of the PDF file using pdfplumber."""
        with pdfplumber.open(pdf_path) as pdf:
            if page_number < len(pdf.pages):
                page = pdf.pages[page_number]
                # Define the footer area
                width = page.width
                height = page.height
                if footer_height > 1:
                    footer_height = 1
                elif footer_height < 0:
                    footer_height = 0
                footer = page.crop((0, height * (1-footer_height), width, height))  # Crop to the specified footer height
                return footer.extract_text()
            else:
                return None

    def find_page_offset(self):
        """Finds the page offset by detecting where the number '1' first appears in the footer."""
        pdf_path = os.path.join(settings.MEDIA_ROOT, self.pdf.name)
        num_pages = len(PdfReader(pdf_path).pages)
        
        for i in range(num_pages):
            footer_text = self.extract_footer_text(pdf_path, i)
            # input(f'test input hit enter to continue {footer_text}')
            if footer_text and re.search(r'\b1\b', footer_text):  # Look for isolated '1'
                self.page_offset = i  # Page where '1' is found is the physical '1'
                return

        self.page_offset = 0  # If '1' is not found, assume no offset

    def set_page_count(self):
        """Sets the page count from the PDF file."""
        if self.pdf and self.page_count <= 1:
            # Construct the full path to the PDF file
            pdf_path = os.path.join(settings.MEDIA_ROOT, "books", self.pdf.name)
            try:
                reader = PdfReader(pdf_path)
                self.page_count = len(reader.pages)
            except Exception as e:
                print(f"Error reading PDF file: {e}")
                self.page_count = 0

    def save(self, *args, **kwargs):
        # Call set_page_count only if pdf is provided and page_count is not set
        if not self.page_count:
            self.set_page_count()

        if self.page_offset == 0:
            self.find_page_offset()

        if not self.index_contents:
            self.update_index_from_pdf()
        # self.update_index_from_pdf()
        
        # Automatically generate slug from title
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else "Unnamed Book"

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
    path = models.FilePathField(path=settings.TOOL_FILES_PATH,match=".*", recursive=True, null=True, blank=True, help_text="Path to the tool")
    code = models.TextField()
    schema = models.JSONField()
    description = models.TextField(null=True, blank=True)
    associated_problem = models.ForeignKey(Problem, null=True,blank=True, related_name='tools', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Check if the directory exists, create it if not
        if self.path and not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)
        if self.code and self.title:
            # Write the code to a file
            file_path = os.path.join(settings.TOOL_FILES_PATH, slugify(self.title)+'.py')
            with open(file_path, 'w') as file:
                file.write(self.code)
            self.path = file_path
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.title:
            return self.title
        elif self.description:
            return self.description[:30] + "..."
        elif self.associated_problem:
            return self.associated_problem.title
        else:
            return 'Unnamed Tool'

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
            self.slug = slugify(self.model_name)
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
