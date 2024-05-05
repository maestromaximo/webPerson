from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'classes', views.ClassViewSet)
router.register(r'schedules', views.ScheduleViewSet)
router.register(r'books', views.BookViewSet)
router.register(r'lessons', views.LessonViewSet)
router.register(r'problems', views.ProblemViewSet)
router.register(r'tools', views.ToolViewSet)
router.register(r'transcripts', views.TranscriptViewSet)
router.register(r'notes', views.NotesViewSet)
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'problemsets', views.ProblemSetViewSet)
router.register(r'tests', views.TestViewSet)


urlpatterns = [
    path('', views.education_home, name='education_home'),
    path('api/', include(router.urls)),
    path('api/lessons/transcribe/', views.upload_and_transcribe, name='transcribe-lesson'),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('chat/', views.chat, name='chat_view'),
    path('chat/class/<slug:class_slug>/', views.chat, name='class_chat'),
    path('chat/lesson/<slug:lesson_slug>/', views.chat, name='lesson_chat'),
    path('chat/assignment/<int:assignment_id>/', views.chat, name='assignment_chat'),
    
    path('chat/fetch-messages/<int:session_id>/', views.fetch_messages, name='fetch_messages_education'),

    path('class/<slug:class_slug>/', views.class_dashboard, name='class_dashboard'),
    path('lesson/<slug:lesson_slug>/', views.lesson_dashboard, name='lesson_dashboard'),

    # path('api/classes/', views.ClassListView.as_view(), name='class-list'),
    # path('api/classes/<int:class_id>/', views.ScheduleDetailView.as_view(), name='schedule-detail'),
    # path('api/lectures/upload/', views.LectureUploadView.as_view(), name='lecture-upload'),
    # path('api/lectures/transcripts/', views.TranscriptListView.as_view(), name='transcript-list'),
    # path('api/notes/upload/', views.NoteUploadView.as_view(), name='note-upload'),
    # path('api/notes/', views.NoteListView.as_view(), name='note-list'),
    # path('api/problems/submit/', views.ProblemSubmissionView.as_view(), name='problem-submit'),
    # path('api/problems/sets/', views.ProblemSetListView.as_view(), name='problem-set-list'),
    # path('api/books/upload/', views.BookUploadView.as_view(), name='book-upload'),
    # path('api/books/<int:book_id>/', views.BookDetailView.as_view(), name='book-detail'),
    # path('api/summaries/generate/', views.SummaryGenerationView.as_view(), name='summary-generate'),
    # path('api/gaps/analyze/', views.GapAnalysisView.as_view(), name='gap-analyze'),
    # path('api/assignments/', views.AssignmentListView.as_view(), name='assignment-list'),
    # path('api/assignments/<int:assignment_id>/', views.AssignmentDetailView.as_view(), name='assignment-detail'),
    # path('api/tests/', views.TestListView.as_view(), name='test-list'),
    # path('api/tests/<int:test_id>/', views.TestDetailView.as_view(), name='test-detail'),
    # path('api/tools/', views.ToolListView.as_view(), name='tool-list'),
    # path('api/tools/<int:tool_id>/', views.ToolDetailView.as_view(), name='tool-detail'),
    # path('lessons/', views.LessonListView.as_view(), name='lesson-list'),
    # path('lessons/<int:pk>/', views.LessonDetailView.as_view(), name='lesson-detail'),

]