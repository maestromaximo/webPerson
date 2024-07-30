import datetime
import json
import os
import shutil
from PyPDF2 import PdfReader
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
import requests
from rest_framework import generics, status, viewsets
from rest_framework.response import Response

from education.forms import LessonForm, TranscriptionUploadForm
from education.utils import extract_the_most_likely_title, generate_chat_completion, get_gpt_response_with_context, query_pinecone, transcribe_audio
# import openai
from .models import ChatSession, Class, Concept, Schedule, Book, Lesson, Problem, StudySheet, Template, Tool, Transcript, Notes, Assignment, ProblemSet, Test, Message
from rest_framework.decorators import api_view
from django.db.models import Count
from .serializers import (ClassSerializer, ScheduleSerializer, BookSerializer, 
                          LessonSerializer, ProblemSerializer, ToolSerializer, 
                          TranscriptSerializer, NotesSerializer, AssignmentSerializer, 
                          ProblemSetSerializer, TestSerializer)
from django.http import FileResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required


from .forms import TemplateSelectionForm, UploadPDFForm
from .utils import calculate_cosine_distance, cleanup_processed_files, cosine_similarity, detect_question_marker, extract_pages_as_images, create_pdf_from_pages, extract_text_from_pdf, generate_embedding, interact_with_gpt
from .utils import generate_study_guide as generate_study_guide_content

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

from django.views.decorators.clickjacking import xframe_options_sameorigin, xframe_options_exempt
from django.core.files.storage import FileSystemStorage

# @xframe_options_sameorigin
def lesson_dashboard(request, lesson_slug):
    # Retrieve the lesson by slug. If not found, a 404 error will be raised.
    selected_lesson = get_object_or_404(Lesson, slug=lesson_slug)

    # Fetch transcripts, notes, problems, tools, and concepts related to the lesson
    lesson_transcripts = Transcript.objects.filter(related_lesson=selected_lesson)
    lesson_notes = Notes.objects.filter(related_lesson=selected_lesson)
    lesson_problems = Problem.objects.filter(related_lessons=selected_lesson).prefetch_related('tools')
    lesson_concepts = Concept.objects.filter(related_lesson=selected_lesson)
    lecture_summary = selected_lesson.get_lecture_summary() if selected_lesson.transcripts.filter(source='Lecture').exists() else "No summary available"
    lecture_exists = selected_lesson.transcripts.filter(source='Lecture').exists()
    student_exists = selected_lesson.transcripts.filter(source='Student').exists()
    notes_exist = lesson_notes.exists()  # Check if there are any notes

    try:
        related_book = selected_lesson.related_class.book if selected_lesson.related_class.book else None
    except:
        related_book = None
        print("no related book found")
    section_title = None
    page_number = None

    if selected_lesson.chapter_title and selected_lesson.chapter_page_number:
        section_title = selected_lesson.chapter_title
        page_number = selected_lesson.chapter_page_number
    elif related_book and related_book.index_contents and lecture_summary not in [None, "No summary available"]:
        try:
            section_title, page_number = extract_the_most_likely_title(book_index=related_book.index_contents, lesson_summary=lecture_summary)
            selected_lesson.chapter_title = section_title
            selected_lesson.chapter_page_number = int(page_number)
            selected_lesson.save()
        except Exception as e:
            print("Error extracting section title and page number", e)
            section_title = None
            page_number = None

    # Prepare the context
    context = {
        'selected_lesson': selected_lesson,
        'lesson_transcripts': lesson_transcripts,
        'lesson_notes': lesson_notes,
        'lesson_problems': lesson_problems,
        'lesson_concepts': lesson_concepts,  # Add concepts to context
        'lecture_summary': lecture_summary,
        'lecture_exists': lecture_exists,
        'student_exists': student_exists,
        'notes_exist': notes_exist,  # Add notes_exist to context
        'section_title': section_title,
        'page_number': page_number,
    }

    return render(request, 'education/lesson_home.html', context)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_concept(request, concept_id):
    try:
        concept = Concept.objects.get(id=concept_id)
        concept.delete()
        return JsonResponse({'success': True})
    except Concept.DoesNotExist:
        return JsonResponse({'success': False}, status=404)
    
@login_required
def assignments_list(request):
    assignments = Assignment.objects.all().order_by('due_date')
    return render(request, 'education/assigment_list.html', {'assignments': assignments})

@login_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    return render(request, 'education/assigment_detail.html', {'assignment': assignment})

@login_required
def download_related_questions(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    questions = assignment.questions.all()
    
    if not questions.exists():
        raise Http404("No related questions found for this assignment.")
    
    output_dir = os.path.join(settings.MEDIA_ROOT, 'temp_questions')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for question in questions:
        question_pdf_path = os.path.join(settings.MEDIA_ROOT, question.answer.name)
        if os.path.exists(question_pdf_path):
            shutil.copy(question_pdf_path, output_dir)
    
    zip_file_path = os.path.join(settings.MEDIA_ROOT, 'temp_questions.zip')
    shutil.make_archive(output_dir, 'zip', output_dir)

    response = FileResponse(open(zip_file_path, 'rb'), as_attachment=True, filename=f'{assignment.related_class.name}_related_questions.zip')
    
    # Cleanup
    shutil.rmtree(output_dir)
    os.remove(zip_file_path)
    
    return response


@staff_member_required
@login_required
def add_lesson_view(request, class_slug):
    class_obj = Class.objects.get(slug=class_slug)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.related_class = class_obj
            lesson.save()
            return redirect('class_dashboard', class_slug=class_slug)
    else:
        form = LessonForm()
    return render(request, 'education/add_lesson.html', {'form': form, 'class': class_obj})

@staff_member_required
@login_required
def add_transcriptions_view(request, lesson_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    if request.method == 'POST':
        form = TranscriptionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            for field in ['lecture_file', 'student_file']:
                audio_file = form.cleaned_data.get(field)
                if audio_file:
                    source = 'Lecture' if 'lecture' in field else 'Student'
                    transcript_text = transcribe_audio(audio_file)  
                    tt, c = Transcript.objects.get_or_create(
                        source=source,
                        related_lesson=lesson
                    )
                    tt.content = transcript_text
                    tt.save()

                lesson.save() # Save the lesson to update the last updated timestamp and begin the analysis process and embedding
            return redirect('lesson_dashboard', lesson_slug=lesson.slug)
    else:
        form = TranscriptionUploadForm()
    
    return render(request, 'education/add_transcriptions.html', {'form': form, 'lesson': lesson})

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
        lesson_slug (str, optional): The slug of the lesson associated with the transcription.
        class_slug (str, optional): The slug of the class associated with the lesson (optional).
        title (str, optional): The title for a newly created lesson if necessary.
    """
    audio_file = request.FILES.get('audio_file')
    source = request.data.get('source')
    lesson_slug = request.data.get('lesson_slug')
    class_slug = request.data.get('class_slug', None)  # Optional class slug
    title = request.data.get('title', 'New Lesson') # Optional title for a new lesson

    if not audio_file or not source or not (lesson_slug or class_slug):
        return Response({'error': 'Missing required parameters.'}, status=400)

    lesson = Lesson.objects.filter(slug=lesson_slug).first()

    if not lesson and class_slug and title: ##Need to add AND title to the if statement
        class_instance = Class.objects.filter(slug=class_slug).first()
        if not class_instance:
            return Response({'error': 'Class does not exist.'}, status=400)
        # Create a new lesson if it does not exist
        lesson = Lesson.objects.create(title=title, related_class=class_instance)

    if not lesson:
        return Response({'error': 'Lesson does not exist and no class provided to create one.'}, status=400)


    try:
        # Transcribe the audio file
        
        transcription_text = transcribe_audio(audio_file)

        # Create a Transcript object
        transcript = Transcript.objects.create(
            content=transcription_text,
            related_lesson=lesson,
            source=source
        )
        lesson.save() # Save the lesson to update the last updated timestamp and begin the analysis process and embedding
        return Response({'transcription': transcription_text, 'source': source, 'lesson':lesson.slug }, status=200)
    except AuthenticationError as e:
        return Response({'error': 'Authentication error.'}, status=401)
    except Exception as e:
        return Response({'error': f'Failed to transcribe audio. {e}'}, status=500)
    
@staff_member_required
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
                        
                        # print(f"DEBUG, related_class.book: {related_class.book}")
                        enhanced_query += f"Most relevant paragraph from '{related_class.book.title+',the lessons book to the question' if book_slug else 'academic resources to the question'}': \"{pinecone_result}\"\n"
                        
                        b_lesson_2 = related_class.find_most_similar_lesson(message_text)
                        if b_lesson_2:
                            best_lessons_final.append(b_lesson_2)
                            enhanced_query += f"Most relevant lesson from this class that could answer the question: {b_lesson_2.title}:\n{b_lesson_2.get_lecture_summary()}\n"
                            print(f"DEBUG, best_lesson_2: {b_lesson_2.title}")
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
                        # print(f"DEBUG, related_class.book: {related_class.book.title}")
                        enhanced_query += f"Most relevant paragraph from '{related_class.book.title +',the lessons book to the question' if book_slug else 'academic resources to the question'}': \"{pinecone_result}\"\n"
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
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.title}.\nFor context, here is the most relevant 500 word long paragraph from the book, likley related to the question,you may use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nThe most related lesson tittle to the question from this class is {b_lesson.title}, and its summary is:\n{b_lesson.get_lecture_summary()}\nPlease answer this user question given the information above and your knowledge:\n\"{message_text}\""
                    elif pinecone_result is not None and b_lesson is None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.title}.\nFor context, here is the most relevant 500 word long paragraph from the book, likley related to the question,you may use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nPlease answer this user question given that:\n\"{message_text}\""
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
                    response_text = get_gpt_response_with_context(session, enhanced_query, class_slug=class_slug)
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
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.title}.\nFor context, here is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nThis is the name of the lesson and its lecture transcript summary:\n{b_lesson.title}:\n{b_lesson.interdisciplinary_connections}\n Strengths in student's understanding: {b_lesson.strengths_in_students_understanding}\n Understanding gaps: {b_lesson.understanding_gaps}\nPlease answer this user question given that:\n\"{message_text}\""
                    elif pinecone_result is not None and b_lesson is None:
                        enhanced_query = f"The user is messaging you with regards to a university class, this is the name of the class {class_instance.name} and it comes from this book {class_instance.book.title}.\nFor context, here is the most relevant 500 word long paragraph from an academic book likely related to the question, use it as a base to answer the question or support it if relevant:\nContext:\"{pinecone_result}\"\nPlease answer this user question given that:\n\"{message_text}\""
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
                    print("Enhanced query with pinecone result", enhanced_query)
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
                    print("Error enhancing query no context",e)
                    response_text = get_gpt_response_with_context(session, message_text)
            else:    
                response_text = get_gpt_response_with_context(session, message_text)

        # Create an assistant message
        Message.objects.create(session=session, text=response_text, role='assistant')

        ##if best lessons is created we need to send the best lessons to the front end maybe add an if statement to handle this
        if best_lessons_final:
            best_lessons_data = [{
                'title': lesson.title,
                'summary': lesson.get_lecture_summary(),
                'url': reverse('lesson_dashboard', kwargs={'lesson_slug': lesson.slug})
            } for lesson in best_lessons_final]
        else:
            best_lessons_data = []

        return JsonResponse({
            'response': response_text,
            'session_id': session.id,
            'best_lessons': best_lessons_data  # Add this line to include lesson details
        })

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



def process_pdf_view(request):
    if request.method == 'POST':
        form = UploadPDFForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['pdf']
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            file_path = fs.path(filename)

            output_dir = os.path.join(settings.MEDIA_ROOT, 'processed_pdfs')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            pdf_reader = PdfReader(file_path)
            images = extract_pages_as_images(file_path)

            question_number = 1
            pages = []
            for i, image in enumerate(images):
                if detect_question_marker(image, i):
                    if pages:
                        output_path = os.path.join(output_dir, f'Q{question_number}.pdf')
                        create_pdf_from_pages(pdf_reader, pages, output_path)
                        question_number += 1
                    pages = [i]
                else:
                    pages.append(i)

            if pages:
                output_path = os.path.join(output_dir, f'Q{question_number}.pdf')
                create_pdf_from_pages(pdf_reader, pages, output_path)

            os.remove(file_path)

            return render(request, 'education/process_pdf.html', {'form': form, 'processed': True})

    else:
        form = UploadPDFForm()

    return render(request, 'education/process_pdf.html', {'form': form, 'processed': False})

def download_processed_files(request):
    output_dir = os.path.join(settings.MEDIA_ROOT, 'processed_pdfs')
    zip_file_path = f'{output_dir}.zip'

    shutil.make_archive(output_dir, 'zip', output_dir)

    response = FileResponse(open(zip_file_path, 'rb'), as_attachment=True, filename='processed_pdfs.zip')

    cleanup_processed_files(output_dir)

    return response

@require_http_methods(["GET"])
def process_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    file_path = assignment.pdf.path
    text = extract_text_from_pdf(file_path)
    
    # Interact with GPT-4 to get the number of questions
    num_questions_response = interact_with_gpt(text, "Please return a JSON that looks like {'number_q': 'number of questions'} where you state the number of main questions on this assignment, only count the main numbers...")
    num_questions = json.loads(num_questions_response).get('number_q', 0)

    questions = []
    for i in range(1, num_questions + 1):
        question_response = interact_with_gpt(text, f"There are a total of {num_questions} questions on this assignment, please extract into a JSON only and in full question #{i} (question number).")
        question_text = json.loads(question_response).get('question', '')
        questions.append({'number': i, 'text': question_text, 'concepts': []})

    # Get all concepts and their embeddings
    all_concepts = Concept.objects.all()
    for concept in all_concepts:
        if not concept.embedding:
            concept.embed()

    # Calculate cosine similarity for each question
    for question in questions:
        question_embedding = generate_embedding(question['text'])
        concept_similarities = []
        for concept in all_concepts:
            similarity = cosine_similarity(question_embedding, concept.embedding)
            concept_similarities.append((concept.description, similarity))
        concept_similarities.sort(key=lambda x: x[1], reverse=True)
        question['concepts'] = [concept[0] for concept in concept_similarities[:5]]

    return JsonResponse({'questions': questions})



@staff_member_required
def study_guide_dashboard(request, class_slug):
    selected_class = get_object_or_404(Class, slug=class_slug)
    if request.method == 'POST':
        form = TemplateSelectionForm(request.POST)
        print(f"Debug: form data: {form.data}")
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"Error in {field}: {error}")
        print(f"Debug: form valid: {form.is_valid()}")
        if form.is_valid():
            template = form.cleaned_data['template']
            lessons = form.cleaned_data['lessons']
            assignments = form.cleaned_data.get('assignments', [])
            lesson_ids = ','.join(str(lesson.id) for lesson in lessons)
            assignment_ids = ','.join(str(assignment.id) for assignment in assignments) if assignments else 'none'
            print(f"Debug: valid form, template: {template}, lessons: {lesson_ids}, assignments: {assignment_ids}")
            return redirect('generate_study_guide', class_slug=class_slug, template_id=template.id, lesson_ids=lesson_ids, assignment_ids=assignment_ids)
    else:
        form = TemplateSelectionForm()
    return render(request, 'education/study_guide_dashboard.html', {'form': form, 'selected_class': selected_class})

@staff_member_required
def generate_study_guide(request, class_slug, template_id, lesson_ids, assignment_ids):
    selected_class = get_object_or_404(Class, slug=class_slug)
    template = get_object_or_404(Template, id=template_id)

    lesson_ids_list = lesson_ids.split(',')
    assignment_ids_list = assignment_ids.split(',') if assignment_ids != 'none' else []

    lessons = Lesson.objects.filter(id__in=lesson_ids_list)
    assignments = Assignment.objects.filter(id__in=assignment_ids_list) if assignment_ids_list else []

    print(f"Debug: Generating study guide for {selected_class.name} using template {template.name}")
    print(f"Debug: Lessons: {lessons}, Assignments: {assignments}")

    # Generate the study guide content
    study_sheet_content = generate_study_guide_content(template, selected_class, lessons, assignments)

    # Save the generated study sheet
    study_sheet = StudySheet.objects.create(class_belongs=selected_class, title=f"Study Guide for {selected_class.name}", content=study_sheet_content)

    return render(request, 'education/study_guide_result.html', {'study_sheet': study_sheet, 'selected_class': selected_class})








    
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