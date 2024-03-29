from django.shortcuts import render
import requests
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
# import openai
from .models import Class, Schedule, Book, Lesson, Problem, Tool, Transcript, Notes, Assignment, ProblemSet, Test
from rest_framework.decorators import api_view
from .serializers import (ClassSerializer, ScheduleSerializer, BookSerializer, 
                          LessonSerializer, ProblemSerializer, ToolSerializer, 
                          TranscriptSerializer, NotesSerializer, AssignmentSerializer, 
                          ProblemSetSerializer, TestSerializer)

# Create your views here.
from openai import AuthenticationError, OpenAI  # Import the OpenAI class
client = OpenAI()


def education_home(request):
    context = {}
    return render(request, 'education/education_home_dark.html', context)



@api_view(['POST'])
def upload_and_transcribe(request):
    if 'audio_file' not in request.FILES or 'source' not in request.data:
        return Response({'error': 'Audio file or source identifier missing.'}, status=400)

    audio_file = request.FILES['audio_file']
    source = request.data['source']

    try:
        transcript = client.audio.transcriptions.create(
            file=audio_file, model="whisper-1"
        )
        return Response({'transcription': transcript['text'], 'source': source}, status=200)
    except AuthenticationError as e:
        return Response({'error': str(e)}, status=401)
    except Exception as e:
        # Catch other possible exceptions and handle them accordingly
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