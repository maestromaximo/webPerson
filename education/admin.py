from django.contrib import admin
from .models import Class, Concept, LessonEmbedding, Prompt, Schedule, Book, Lesson, Problem, StudySheet, Template, Tool, Transcript, Notes, Assignment, ProblemSet, Test, Message, ChatSession, AssigmentQuestion
# GPTInstance
class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 1  # Number of extra forms to display

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

class ProblemInline(admin.TabularInline):
    model = Problem
    extra = 1

class ToolInline(admin.TabularInline):
    model = Tool
    extra = 1

class TranscriptInline(admin.TabularInline):
    model = Transcript
    extra = 1

class NotesInline(admin.TabularInline):
    model = Notes
    extra = 1

class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1

class ProblemSetInline(admin.TabularInline):
    model = ProblemSet.related_lessons.through  # Assuming you want to manage this through the Lesson
    extra = 1

class TestInline(admin.TabularInline):
    model = Test
    extra = 1

class MessageInline(admin.TabularInline):
    model = Message
    extra = 1  # Allows adding at least one new message when creating a session
    fields = ['text', 'role', 'timestamp']
    readonly_fields = ['timestamp']
    can_delete = True
    show_change_link = True

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ScheduleInline, LessonInline, AssignmentInline, TestInline]

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_belongs', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'class_belongs')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_count', 'related_class', 'embedded')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title', 'related_class__name')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'related_class', 'analyzed')
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ('related_class',)
    inlines = [TranscriptInline, NotesInline, ProblemSetInline]

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('description', 'problem_type', 'answer_type')
    list_filter = ('problem_type', 'answer_type')
    inlines = [ToolInline]

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('title','description', 'associated_problem')
    list_filter = ('associated_problem',)
    search_fields = ('title', 'description')

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('content', 'source', 'timestamp', 'related_lesson')
    list_filter = ('source', 'related_lesson')

@admin.register(Notes)
class NotesAdmin(admin.ModelAdmin):
    list_display = ('related_lesson', 'file')
    list_filter = ('related_lesson', 'name')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'due_date', 'related_class')
    list_filter = ('due_date', 'related_class')

@admin.register(ProblemSet)
class ProblemSetAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    filter_horizontal = ('related_lessons',)  # This allows you to select multiple lessons for a problem set in admin.

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('related_class', 'date', 'duration')
    list_filter = ('date', 'related_class')

# @admin.register(Prompt)
# class PromptAdmin(admin.ModelAdmin):
#     list_display = ('title', 'category', 'active')
#     list_filter = ('active', 'category')
#     search_fields = ('title', 'prompt', 'description')
#     actions = ['make_active', 'make_inactive']

#     @admin.action(description='Mark selected prompts as active')
#     def make_active(self, request, queryset):
#         queryset.update(active=True)

#     @admin.action(description='Mark selected prompts as inactive')
#     def make_inactive(self, request, queryset):
#         queryset.update(active=False)

# @admin.register(GPTInstance)
# class GPTInstanceAdmin(admin.ModelAdmin):
#     list_display = ('model_name', 'use_embeddings', 'web_access', 'default_path')
#     prepopulated_fields = {"slug": ("model_name",)}
#     list_filter = ('model_name', 'use_embeddings', 'web_access')
#     search_fields = ('model_name',)
#     filter_horizontal = ('tools',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    inlines = [MessageInline]

    def get_ordering(self, request):
        return ['created_at']  # Order by creation time by default


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'text', 'role', 'timestamp')
    list_filter = ('timestamp', 'role')
    search_fields = ('text', 'session__id')
    readonly_fields = ['timestamp']

@admin.register(LessonEmbedding)
class LessonEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'created_at', 'updated_at')
    list_filter = ('lesson',)
    search_fields = ('lesson__title',)

@admin.register(AssigmentQuestion)
class AssigmentQuestionAdmin(admin.ModelAdmin):
    list_display = ('section', 'related_assignment')
    list_filter = ('related_assignment', 'section')
    search_fields = ('question', 'section')


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ('title', 'related_class', 'related_lesson', 'approved')
    list_filter = ('approved', 'related_class', 'related_lesson', 'title')
    search_fields = ('title', 'description', 'notes')
    ordering = ('title',)
    fields = ('related_class', 'related_lesson', 'title', 'description', 'notes', 'approved')



@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'slug')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('template', 'order', 'prompt_text')
    list_filter = ('template',)
    search_fields = ('prompt_text',)
    ordering = ('template', 'order')

@admin.register(StudySheet)
class StudySheetAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_belongs')
    list_filter = ('class_belongs',)
    search_fields = ('title', 'content')
    ordering = ('class_belongs', 'title')
    readonly_fields = ('content',)
