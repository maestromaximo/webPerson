from django.contrib import admin
from .models import Class, Schedule, Book, Lesson, Problem, Tool, Transcript, Notes, Assignment, ProblemSet, Test

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

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    inlines = [ScheduleInline, LessonInline, AssignmentInline, TestInline]

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_belongs', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'class_belongs')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_count', 'related_class')
    search_fields = ('title', 'related_class__name')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'related_class')
    list_filter = ('related_class',)
    inlines = [TranscriptInline, NotesInline, ProblemSetInline]

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('description', 'problem_type', 'answer_type')
    list_filter = ('problem_type', 'answer_type')
    inlines = [ToolInline]

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('description', 'associated_problem')
    list_filter = ('associated_problem',)

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('content', 'source', 'timestamp', 'related_lesson')
    list_filter = ('source', 'related_lesson')

@admin.register(Notes)
class NotesAdmin(admin.ModelAdmin):
    list_display = ('related_lesson', 'file')

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
