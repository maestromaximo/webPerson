import os
import re
from typing import List
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from PyPDF2 import PdfReader
import pdfplumber
from tqdm import tqdm
from .utils import extract_toc_text, extract_toc_until_page, find_first_toc_page, parse_toc, upload_book_to_index,generate_chat_completion
from django.contrib.auth.models import User

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
    embedded = models.BooleanField(default=False, help_text="If the book is embedded in the website, set this to True.")
    
    def update_index_from_pdf(self, skip_from_page=2, continuous=True):
        """Updates the index_contents field by extracting and parsing the ToC from the PDF."""
        pdf_path = os.path.join(settings.MEDIA_ROOT, self.pdf.name)
        toc_dict = find_first_toc_page(pdf_path, skip_from_page=skip_from_page, continuous=continuous)
        if toc_dict:
            self.index_contents = str(toc_dict)
        else:
            self.index_contents = {}

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

    def embed_and_upload(self):
        """Embed the book text and upload the embeddings to Pinecone."""
        if not self.embedded:
            pdf_path = self.pdf.path  # Adjust based on your actual storage settings
            book_name_slug = self.slug or slugify(self.title)
            # input(f'DEBUG: Uploading book to index this is the path {pdf_path}')
            upload_book_to_index(pdf_path, book_name_slug)
            self.embedded = True
            self.save()

    def save(self, *args, **kwargs):
        # Call set_page_count only if pdf is provided and page_count is not set

        # Automatically generate slug from title
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        if not self.page_count:
            self.set_page_count()
        if self.page_offset == 0:
            self.find_page_offset()
        if not self.index_contents:
            self.update_index_from_pdf()
        # self.update_index_from_pdf()
        self.embed_and_upload()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else "Unnamed Book"

class Lesson(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    related_class = models.ForeignKey(Class, related_name='lessons', on_delete=models.CASCADE)
    slug = models.SlugField(null=True, blank=True)
    analyzed = models.BooleanField(default=False)  # New field to track analysis status

    interdisciplinary_connections = models.TextField(null=True, blank=True)
    real_world_applications = models.TextField(null=True, blank=True)
    creative_synthesis_of_ideas = models.TextField(null=True, blank=True)
    detail_level_comparison = models.TextField(null=True, blank=True)
    accuracy_of_information = models.TextField(null=True, blank=True)
    direct_concept_comparison = models.TextField(null=True, blank=True)
    strengths_in_students_understanding = models.TextField(null=True, blank=True)
    understanding_gaps = models.TextField(null=True, blank=True)
    comparison_of_key_concepts = models.TextField(null=True, blank=True)

    def generate_analysis(self):
        """Generates an analysis for the lesson if both student and lecture transcripts exist and are summarized."""
        lecture_transcript = self.transcripts.filter(source='Lecture').first()
        student_transcript = self.transcripts.filter(source='Student').first()

        if not self.analyzed and lecture_transcript and student_transcript:
            print("Summarizing transcripts...")
            if not lecture_transcript.summarized:
                lecture_transcript.summarize()
            if not student_transcript.summarized:
                student_transcript.summarize()

        if lecture_transcript and student_transcript and lecture_transcript.summarized and student_transcript.summarized:
            prompts = {
                "interdisciplinary_connections": ("Examine the following transcript for connections to other disciplines or fields of study:\nTranscript: {lecture}", ['lecture']),
                "real_world_applications": ("Identify and describe real-world applications or examples of concepts discussed in the following transcript summary:\nTranscript: {lecture}", ['lecture']),
                "creative_synthesis_of_ideas": ("Encourage a creative synthesis of the ideas discussed in the following transcript:\nTranscript: {lecture}", ['lecture']),
                "detail_level_comparison": ("Compare the level of detail between the lecture's content and the student's summary. Please be logical and thorough in your comparison.\nStudent's Transcript: {student}\nLecture's Transcript: {lecture}", ['student', 'lecture']),
                "accuracy_of_information": ("Evaluate the accuracy of the information in the student's summary compared to the lecture's transcript.\nStudent's Transcript: {student}\nLecture's Transcript: {lecture}", ['student', 'lecture']),
                "direct_concept_comparison": ("Directly compare the concepts and topics covered in the lecture transcript with those mentioned in the student's summary.\nStudent's Transcript: {student}\nLecture's Transcript: {lecture}", ['student', 'lecture']),
                "strengths_in_students_understanding": ("Analyze the student's summary to identify strengths in their understanding given the lecture.\nStudent's Summary: {student}", ['student']),
                "understanding_gaps": ("Based on the lecture transcript and the student's summary, identify any themes the student may have misunderstood or is not applying correctly or missing completely.\nStudent's Transcript: {student}\nLecture's Transcript: {lecture}", ['student', 'lecture']),
                "comparison_of_key_concepts": ("Identify and compare key concepts mentioned in both the lecture transcript and the student's summary.\nStudent's Transcript: {student}\nLecture's Transcript: {lecture}", ['student', 'lecture']),
            }

            for field, (prompt_template, required_transcripts) in tqdm(prompts.items(), desc="Generating Analysis for Lesson"):
                prompt = prompt_template.format(
                    lecture=lecture_transcript.summarized if 'lecture' in required_transcripts else "",
                    student=student_transcript.summarized if 'student' in required_transcripts else ""
                )
                setattr(self, field, generate_chat_completion(prompt))
            
            self.analyzed = True
            self.save()



    def __str__(self):
        return f"{self.title or 'Unnamed Lesson'} - {self.related_class.name}"
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        if not self.analyzed:
            self.generate_analysis()
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
    summarized = models.TextField(null=True, blank=True)  # New field for storing summaries

    def summarize(self):
        """Generate a summary for this transcript using an AI model."""
        if not self.summarized:  # Check if the summary is already generated
            prompt = f"Provide only a well thought summary of the following transcript of a university lesson, you must capture the essence of the lesson and its most important points, equations, and ideas, write as much as you want.\nTranscript:\"{self.content}\""
            self.summarized = generate_chat_completion(prompt, use_gpt4=True)
            self.save()

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

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat Session {self.id} - User {self.user.username}"

class Message(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.role} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {self.text[:50]}..."
