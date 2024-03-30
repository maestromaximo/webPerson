import datetime
from django.shortcuts import get_object_or_404, render
import requests
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
# import openai
from .models import Class, Schedule, Book, Lesson, Problem, Tool, Transcript, Notes, Assignment, ProblemSet, Test
from rest_framework.decorators import api_view
from django.db.models import Count
from .serializers import (ClassSerializer, ScheduleSerializer, BookSerializer, 
                          LessonSerializer, ProblemSerializer, ToolSerializer, 
                          TranscriptSerializer, NotesSerializer, AssignmentSerializer, 
                          ProblemSetSerializer, TestSerializer)

# Create your views here.
from openai import AuthenticationError, OpenAI  # Import the OpenAI class
client = OpenAI()



def education_home(request):
    # Get all classes
    active_classes = Class.objects.all()
    
    # Upcoming class
    now = datetime.datetime.now()
    upcoming_schedules = Schedule.objects.filter(start_time__gt=now).order_by('start_time')
    if upcoming_schedules:
        upcoming_class = upcoming_schedules.first().class_belongs
    else:
        upcoming_class = None

    # Upcoming tests
    upcoming_tests = Test.objects.filter(date__gt=now).order_by('date')[:5]

    # Most reviewed lesson - you will need to define the logic for this
    most_reviewed_lesson = Lesson.objects.annotate(num_reviews=Count('transcripts')).first()

    context = {
        'active_classes': active_classes,
        'upcoming_class': upcoming_class,
        'upcoming_tests': upcoming_tests,
        'most_reviewed_lesson': most_reviewed_lesson,
    }

    return render(request, 'education/education_home_dark.html', context)

def class_dashboard(request, class_slug):
    # Retrieve the class by slug. If not found, a 404 error will be raised.
    selected_class = get_object_or_404(Class, slug=class_slug)
    
    # Fetch additional data needed for the class dashboard
    class_schedules = Schedule.objects.filter(class_belongs=selected_class)
    class_books = Book.objects.filter(related_class=selected_class)
    class_assignments = Assignment.objects.filter(related_class=selected_class)
    class_tests = Test.objects.filter(related_class=selected_class)
    class_lessons = Lesson.objects.filter(related_class=selected_class)

    # Prepare the context
    context = {
        'selected_class': selected_class,
        'class_schedules': class_schedules,
        'class_books': class_books,
        'class_assignments': class_assignments,
        'class_tests': class_tests,
        'class_lessons': class_lessons,
    }

    return render(request, 'education/class_home.html', context)

def lesson_dashboard(request, lesson_slug):
    # Retrieve the lesson by slug. If not found, a 404 error will be raised.
    selected_lesson = get_object_or_404(Lesson, slug=lesson_slug)

    # Fetch additional data needed for the lesson dashboard
    lesson_transcripts = Transcript.objects.filter(related_lesson=selected_lesson)
    lesson_notes = Notes.objects.filter(related_lesson=selected_lesson)
    lesson_problems = Problem.objects.filter(related_lessons=selected_lesson)
    lesson_tools = Tool.objects.filter(associated_problem__in=lesson_problems)

    # Prepare the context
    context = {
        'selected_lesson': selected_lesson,
        'lesson_transcripts': lesson_transcripts,
        'lesson_notes': lesson_notes,
        'lesson_problems': lesson_problems,
        'lesson_tools': lesson_tools,
    }

    return render(request, 'education/lesson_home.html', context)


@api_view(['POST'])
def upload_and_transcribe(request):
    """
    Uploads an audio file, transcribes it, and creates a Transcript object.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A Response object with the transcription text, source, and lesson slug if successful.
                      Otherwise, returns a Response object with an error message and corresponding status code.

    Raises:
        ValueError: If any of the required parameters (audio_file, source, lesson_slug) are missing.
        ValueError: If the provided class_slug does not correspond to an existing Class object.
        ValueError: If the lesson does not exist and no class_slug is provided to create one.

    Full Args:
        request (HttpRequest): The HTTP request object.
        audio_file (File): The audio file to be transcribed.
        source (str): The source of the audio file.
        lesson_slug (str): The slug of the lesson associated with the transcription.
        class_slug (str, optional): The slug of the class associated with the lesson (optional).

    """
    audio_file = request.FILES.get('audio_file')
    source = request.data.get('source')
    lesson_slug = request.data.get('lesson_slug')
    class_slug = request.data.get('class_slug', None)  # Optional class slug

    if not audio_file or not source or not lesson_slug:
        return Response({'error': 'Missing required parameters.'}, status=400)

    lesson = Lesson.objects.filter(slug=lesson_slug).first()

    if not lesson and class_slug:
        class_instance = Class.objects.filter(slug=class_slug).first()
        if not class_instance:
            return Response({'error': 'Class does not exist.'}, status=400)
        # Create a new lesson if it does not exist
        lesson = Lesson.objects.create(title='New Lesson', related_class=class_instance)

    if not lesson:
        return Response({'error': 'Lesson does not exist and no class provided to create one.'}, status=400)


    try:
        # Transcribe the audio file
        transcript_response = client.audio.transcriptions.create(
            file=audio_file, model="whisper-1"
        )
        transcription_text = transcript_response['text']

        # Create a Transcript object
        transcript = Transcript.objects.create(
            content=transcription_text,
            related_lesson=lesson,
            source=source
        )

        return Response({'transcription': transcription_text, 'source': source, 'lesson':lesson.slug }, status=200)
    except AuthenticationError as e:
        return Response({'error': 'Authentication error.'}, status=401)
    except Exception as e:
        return Response({'error': 'Failed to transcribe audio.'}, status=500)
    
    
class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

class ProblemViewSet(viewsets.ModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer

class ToolViewSet(viewsets.ModelViewSet):
    queryset = Tool.objects.all()
    serializer_class = ToolSerializer

class TranscriptViewSet(viewsets.ModelViewSet):
    queryset = Transcript.objects.all()
    serializer_class = TranscriptSerializer

class NotesViewSet(viewsets.ModelViewSet):
    queryset = Notes.objects.all()
    serializer_class = NotesSerializer

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

class ProblemSetViewSet(viewsets.ModelViewSet):
    queryset = ProblemSet.objects.all()
    serializer_class = ProblemSetSerializer

class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer







# class LessonListView(generics.ListAPIView):
#     queryset = Lesson.objects.all()
#     serializer_class = LessonSerializer

# class LessonDetailView(generics.RetrieveAPIView):
#     queryset = Lesson.objects.all()
#     serializer_class = LessonSerializer

# class ClassListView(generics.ListAPIView):
#     queryset = Class.objects.all()
#     serializer_class = ClassSerializer

# class ScheduleDetailView(generics.RetrieveAPIView):
#     queryset = Schedule.objects.all()
#     serializer_class = ScheduleSerializer

# class LectureUploadView(generics.CreateAPIView):
#     queryset = Transcript.objects.all()
#     serializer_class = TranscriptSerializer

# class TranscriptListView(generics.ListAPIView):
#     queryset = Transcript.objects.all()
#     serializer_class = TranscriptSerializer

# class NoteUploadView(generics.CreateAPIView):
#     queryset = Notes.objects.all()
#     serializer_class = NotesSerializer

# class NoteListView(generics.ListAPIView):
#     queryset = Notes.objects.all()
#     serializer_class = NotesSerializer

# class ProblemSubmissionView(generics.CreateAPIView):
#     queryset = Problem.objects.all()
#     serializer_class = ProblemSerializer

# class ProblemSetListView(generics.ListAPIView):
#     queryset = ProblemSet.objects.all()
#     serializer_class = ProblemSetSerializer

# class BookUploadView(generics.CreateAPIView):
#     queryset = Book.objects.all()
#     serializer_class = BookSerializer

# class BookDetailView(generics.RetrieveAPIView):
#     queryset = Book.objects.all()
#     serializer_class = BookSerializer

# class SummaryGenerationView(generics.ListCreateAPIView):
#     # This would be a custom view that interacts with your summary generation logic
#     pass

# class GapAnalysisView(generics.ListCreateAPIView):
#     # This would be a custom view for analyzing gaps; might require specialized logic
#     pass

# class AssignmentListView(generics.ListAPIView):
#     queryset = Assignment.objects.all()
#     serializer_class = AssignmentSerializer

# class AssignmentDetailView(generics.RetrieveAPIView):
#     queryset = Assignment.objects.all()
#     serializer_class = AssignmentSerializer

# class TestListView(generics.ListAPIView):
#     queryset = Test.objects.all()
#     serializer_class = TestSerializer

# class TestDetailView(generics.RetrieveAPIView):
#     queryset = Test.objects.all()
#     serializer_class = TestSerializer

# class ToolListView(generics.ListAPIView):
#     queryset = Tool.objects.all()
#     serializer_class = ToolSerializer

# class ToolDetailView(generics.RetrieveAPIView):
#     queryset = Tool.objects.all()
#     serializer_class = ToolSerializer