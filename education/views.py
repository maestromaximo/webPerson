import datetime
import json
from django.shortcuts import get_object_or_404, render
import requests
from rest_framework import generics, status, viewsets
from rest_framework.response import Response

from education.utils import generate_chat_completion, get_gpt_response_with_context, query_pinecone
# import openai
from .models import ChatSession, Class, Schedule, Book, Lesson, Problem, Tool, Transcript, Notes, Assignment, ProblemSet, Test, Message
from rest_framework.decorators import api_view
from django.db.models import Count
from .serializers import (ClassSerializer, ScheduleSerializer, BookSerializer, 
                          LessonSerializer, ProblemSerializer, ToolSerializer, 
                          TranscriptSerializer, NotesSerializer, AssignmentSerializer, 
                          ProblemSetSerializer, TestSerializer)
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
from openai import AuthenticationError, OpenAI  # Import the OpenAI class
client = OpenAI()


@login_required
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

@login_required
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

@login_required
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
    

@login_required
def chat(request, class_slug=None, lesson_slug=None):
    # Initialize context with chat sessions
    context = {
        'chat_sessions': ChatSession.objects.filter(user=request.user).order_by('-created_at'),
        'current_session_id': None
    }
    
    # Use slugs from the URL or fall back to the POST data
    # class_slug = class_slug
    # lesson_slug = lesson_slug 

    # If accessed via a class or lesson page
    if class_slug:
        context['current_class'] = get_object_or_404(Class, slug=class_slug)
    if lesson_slug:
        lesson = get_object_or_404(Lesson, slug=lesson_slug)
        context['current_lesson'] = lesson
        context['current_class'] = lesson.related_class  # This assumes that each lesson has a related class

    if request.method == 'GET':
        # Render the chat template with the additional context
        return render(request, 'education/chat.html', context)

    elif request.method == 'POST':
        data = json.loads(request.body)
        message_text = data.get('message')
        session_id = data.get('session_id', None)
        super_search = data.get('super_search', False)
        class_slug = data.get('class_slug', None)
        lesson_slug = data.get('lesson_slug', None)
        new_session_created = False
        best_lessons_created = False
        best_lessons_final = []
        if not message_text:
            return HttpResponseBadRequest("Message text is required.")

        # Find or create a chat session
        session = ChatSession.objects.filter(id=session_id, user=request.user).first()
        if not session:
            session = ChatSession.objects.create(user=request.user)
            new_session_created = True

        # Create a user message
        Message.objects.create(session=session, text=message_text, role='user')

        # Generate a response with context if any
        if lesson_slug:
            lesson = get_object_or_404(Lesson, slug=lesson_slug)
            related_class = lesson.related_class
            
            if new_session_created:
                enhanced_query = f"This chat is about the lesson '{lesson.title}' from the class '{related_class.name}', here is information related to this lesson and the student:\nSummary: {lesson.get_lecture_summary()}\n Gaps: {lesson.understanding_gaps}\n Strengths: {lesson.strengths_in_students_understanding}, Accuracy: {lesson.accuracy_of_information}\n Concepts: {lesson.comparison_of_key_concepts}.\nGiven this information, please answer the following question from the student:\n\"{message_text}\"\n"
                if super_search:
                    try:
                        book_slug = related_class.book.slug if related_class.book else None
                        pinecone_result = query_pinecone(message_text, namespace=book_slug) if book_slug else query_pinecone(message_text)
                        enhanced_query += f"Most relevant paragraph from '{related_class.book.title+",the lessons book to the question" if book_slug else 'academic resources to the question'}': \"{pinecone_result}\"\n"
                        b_lesson_2 = related_class.find_most_similar_lesson(message_text)
                        if b_lesson_2:
                            best_lessons_final.append(b_lesson_2)
                        enhanced_query += f"Most relevant lesson from this class that could answer the question: {b_lesson_2.title}:\n{b_lesson_2.get_lecture_summary()}\n"
                    except Exception as e:
                        print("Error querying Pinecone", e)
                 
                enhanced_query += f"Given all of the contextual information above, please answer the following question from the student:\n\"{message_text}\""
                response_text = get_gpt_response_with_context(session, enhanced_query)
            else:
                enhanced_query = ""
                if super_search:
                    try:
                        book_slug = related_class.book.slug if related_class.book else None
                        pinecone_result = query_pinecone(message_text, namespace=book_slug) if book_slug else query_pinecone(message_text)
                        enhanced_query += f"Most relevant paragraph from '{related_class.book.title+",the lessons book to the question" if book_slug else 'academic resources to the question'}': \"{pinecone_result}\"\n"
                        b_lesson_2 = related_class.find_most_similar_lesson(message_text)
                        if b_lesson_2:
                            best_lessons_final.append(b_lesson_2)
                        enhanced_query += f"Most relevant lesson from this class that could answer the last question: {b_lesson_2.title}:\n{b_lesson_2.get_lecture_summary()}\n"
                    except Exception as e:
                        print("Error querying Pinecone", e)
                    enhanced_query += f"Given all of the contextual information above, please answer the following question from the student:\n\"{message_text}\""
                    response_text = get_gpt_response_with_context(session, enhanced_query, lesson_slug=lesson_slug)
                else:
                    response_text = get_gpt_response_with_context(session, message_text, lesson_slug=lesson_slug)

        elif class_slug:
            # print(f'class_slug: {class_slug}')
            class_instance = get_object_or_404(Class, slug=class_slug)
            if new_session_created:
                if super_search: ## if super search then we need to enhance the query with the most accurate material from both pinecone related to the book of this class and the most accurate lesson from this class, specifically the name of the lesson and its lecture transcript summary
                    pinecone_result = None
                    try:
                        ##getting the book slug to query as a namespace
                        related_book_slug = class_instance.book.slug
                        if isinstance(related_book_slug, str):
                            pinecone_result = query_pinecone(message_text, namespace=related_book_slug)
                        else:
                            pinecone_result = None
                    except Exception as e:
                        print("Error querying pinecone", e)
                        pinecone_result = None
                    ##now that we have pinecone, either none or a str lets get the lesson
                    b_lesson = None
                    try:
                        b_lesson: Lesson = class_instance.find_most_similar_lesson(message_text)
                        if b_lesson:
                            best_lessons_final.append(b_lesson)
                    except Exception as e:
                        print("Error finding best lesson", e)
                        b_lesson = None
                    ##Now we have the pinecone result and the best lesson, we can now enhance the query with this information but if we miss any of them we just enhance with the ones we do have
                    enhanced_query = None
                    if pinecone_result is not None and b_lesson is not None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.name}.\nFor context, here is the most relevant 500 word long paragraph from the book, likley related to the question,you may use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nThe most related lesson tittle to the question from this class is {b_lesson.title}, and its summary is:\n{b_lesson.get_lecture_summary()}\nPlease answer this user question given the information above and your knowledge:\n\"{message_text}\""
                    elif pinecone_result is not None and b_lesson is None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.name}.\nFor context, here is the most relevant 500 word long paragraph from the book, likley related to the question,you may use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nPlease answer this user question given that:\n\"{message_text}\""
                    elif pinecone_result is None and b_lesson is not None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name}.\nFor context, t he most related lesson tittle to the question from this class is {b_lesson.title}, and its summary is:\n{b_lesson.get_lecture_summary()}\nPlease answer this user question given the information above and your knowledge:\n\"{message_text}\""
                    else:## if all fails and we get two nones, lets try to do a easy super search of pinecone with no namespace within a try catch and if that fails then just a normal response text
                        try:
                            pinecone_result = query_pinecone(message_text)
                            enhanced_query = f"This is a system message from a RAG system, attached is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant.\nContext:\"{pinecone_result}\"\nNow this is the original question from the user, please answer it accordingly now:\n\"{message_text}\""
                        except Exception as e:
                            print("Error enhancing query defaulting to normal search",e)
                            enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name}.\nPlease answer this user question given that:\n\"{message_text}\""
                    response_text = get_gpt_response_with_context(session, enhanced_query)
                else:
                    enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name}.\nPlease answer this user question given that:\n\"{message_text}\""
                    response_text = generate_chat_completion(class_instance, message_text)
            else:
                if super_search:
                    pinecone_result = None
                    try:
                        ##getting the book slug to query as a namespace
                        related_book_slug = class_instance.book.slug
                        if isinstance(related_book_slug, str):
                            pinecone_result = query_pinecone(message_text, namespace=related_book_slug)
                        else:
                            pinecone_result = None
                    except Exception as e:
                        print("Error querying pinecone", e)
                        pinecone_result = None
                    ##now that we have pinecone, either none or a str lets get the lesson
                    b_lesson = None
                    try:
                        b_lesson: Lesson = class_instance.find_most_similar_lesson(message_text)
                        if b_lesson:
                            best_lessons_final.append(b_lesson)
                    except Exception as e:
                        print("Error finding best lesson", e)
                        b_lesson = None
                    ##Now we have the pinecone result and the best lesson, we can now enhance the query with this information but if we miss any of them we just enhance with the ones we do have
                    enhanced_query = None
                    if pinecone_result is not None and b_lesson is not None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.name}.\nFor context, here is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nThis is the name of the lesson and its lecture transcript summary:\n{b_lesson.title}:\n{b_lesson.interdisciplinary_connections}\n Strengths in student's understanding: {b_lesson.strengths_in_students_understanding}\n Understanding gaps: {b_lesson.understanding_gaps}\nPlease answer this user question given that:\n\"{message_text}\""
                    elif pinecone_result is not None and b_lesson is None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.name}.\nFor context, here is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nPlease answer this user question given that:\n\"{message_text}\""
                    elif pinecone_result is None and b_lesson is not None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name}.\nFor context, this is the name of the lesson and its lecture transcript summary:\n{b_lesson.title}:\n{b_lesson.interdisciplinary_connections}\n Strengths in student's understanding: {b_lesson.strengths_in_students_understanding}\n Understanding gaps: {b_lesson.understanding_gaps}\nPlease answer this user question given that:\n\"{message_text}\""
                    else:## if all fails and we get two nones, lets try to do a easy super search of pinecone with no namespace within a try catch and if that fails then just a normal response text
                        try:
                            pinecone_result = query_pinecone(message_text)
                            enhanced_query = f"This is a system message from a RAG system, attached is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant.\nContext:\"{pinecone_result}\"\nNow this is the original question from the user, please answer it accordingly now:\n\"{message_text}\""
                        except Exception as e:
                            print("Error enhancing query defaulting to normal search",e)
                            enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name}.\nPlease answer this user question given that:\n\"{message_text}\""
                    response_text = get_gpt_response_with_context(session, enhanced_query)
                else:
                    response_text = get_gpt_response_with_context(session, message_text, class_slug=class_slug)
        else:
            # print(f'No context')
            if super_search:
                try:
                    pinecone_result = query_pinecone(message_text)
                    enhanced_query = f"This is a system message from a RAG system, attached is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant.\nContext:\"{pinecone_result}\"\nNow this is the original question from the user, please answer it accordingly now:\n\"{message_text}\""
                    
                    ### Here as an extra we can find the most relevant lesson, from all classes and return the class and lesson to the user but only if first question. UPDATE: we look now at all classes and retrive the best lesson from each
                    if new_session_created: ##only run this if its the first question and it is a super search
                        all_classes = Class.objects.all()
                        best_lessons = []
                        for cclass in all_classes:
                            try:
                                b_lesson: Lesson = cclass.find_most_similar_lesson(message_text)
                                if b_lesson:
                                    best_lessons.append(b_lesson)
                            except Exception as e:
                                print("Error finding best lesson", e)
                        if best_lessons:
                            best_lessons_created = True
                            best_lessons_final = best_lessons ## we can then modify the return and front end to display this on the message as kind of like a suggestion that can be cliocked to take you to the lessons page
                    
                    response_text = get_gpt_response_with_context(session, enhanced_query)
                except Exception as e:
                    print("Error enhancing query",e)
                    response_text = get_gpt_response_with_context(session, message_text)
            else:    
                response_text = get_gpt_response_with_context(session, message_text)

        # Create an assistant message
        Message.objects.create(session=session, text=response_text, role='assistant')

        return JsonResponse({'response': response_text, 'session_id': session.id})

@csrf_exempt
@require_http_methods(["GET"])
def fetch_messages(request, session_id):
    # Ensure user is authenticated and correct session is accessed
    print(f'Debug: {session_id}, in fetch_messages')
    if not request.user.is_authenticated:
        return HttpResponseBadRequest("User not authenticated.")

    session = ChatSession.objects.filter(id=session_id, user=request.user).first()
    if not session:
        return HttpResponseBadRequest("Invalid session.")

    messages = [{'text': msg.text, 'is_user_message': (msg.role == 'user')} for msg in session.messages.all().order_by('timestamp')]
    return JsonResponse({'messages': messages})

    
    
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