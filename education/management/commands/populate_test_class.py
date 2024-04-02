from django.core.management.base import BaseCommand
from django.utils import timezone
from education.models import Class, Schedule, Lesson, Problem, Transcript, Assignment, Test

class Command(BaseCommand):
    help = "Populates the database with a rich test Class, including schedules, assignments, lessons, and transcripts"

    def handle(self, *args, **options):
        # Create an Algebra class instance
        algebra_class, _ = Class.objects.get_or_create(
            name='Algebra 101',
            subject='Algebra',
            defaults={'slug': 'algebra-101'}
        )

        # Create schedules for the Algebra class
        Schedule.objects.get_or_create(
            class_belongs=algebra_class,
            day_of_week='Monday',
            start_time=timezone.now().time(),
            end_time=(timezone.now() + timezone.timedelta(hours=1)).time()
        )
        Schedule.objects.get_or_create(
            class_belongs=algebra_class,
            day_of_week='Wednesday',
            start_time=timezone.now().time(),
            end_time=(timezone.now() + timezone.timedelta(hours=1)).time()
        )

        # Create an assignment for the Algebra class
        Assignment.objects.get_or_create(
            description="Complete the problem set on quadratic equations.",
            due_date=timezone.now() + timezone.timedelta(days=7),
            related_class=algebra_class
        )

        # Create lessons for the Algebra class
        lesson1, _ = Lesson.objects.get_or_create(
            title='Introduction to Algebra',
            related_class=algebra_class,
            defaults={'slug': 'introduction-to-algebra'}
        )
        lesson2, _ = Lesson.objects.get_or_create(
            title='Quadratic Equations',
            related_class=algebra_class,
            defaults={'slug': 'quadratic-equations'}
        )

        # Create problems for the lessons
        problem1, _ = Problem.objects.get_or_create(
            title='Solve Linear Equations',
            description='Solve the following linear equations.',
            steps='List of steps to solve linear equations.',
            solution='Solutions to the linear equations.',
            problem_type='Fixed Answer',
            answer_type='Number'
        )
        problem1.related_lessons.add(lesson1)

        problem2, _ = Problem.objects.get_or_create(
            title='Factor Quadratic Equations',
            description='Factor the following quadratic equations.',
            steps='List of steps to factor quadratic equations.',
            solution='Factored forms of the quadratic equations.',
            problem_type='Fixed Answer',
            answer_type='Number'
        )
        problem2.related_lessons.add(lesson2)

        # Add lecture transcripts to the lessons
        Transcript.objects.get_or_create(
            content=(
                "Today's lecture introduced the fundamental concepts of Algebra, "
                "including variables, constants, and equations. We explored how "
                "to solve simple linear equations and discussed their practical applications."
            ),
            source='Lecture',
            related_lesson=lesson1
        )

        # Add student transcripts to the lessons (simulating a less formal summary)
        Transcript.objects.get_or_create(
            content=(
                "We started Algebra with basic stuff like finding x in equations. "
                "It's kinda like a treasure hunt, but with numbers and letters. "
                "I guess this will help me balance my budget better!"
            ),
            source='Student',
            related_lesson=lesson1
        )

        # Add lecture transcripts for the second lesson
        Transcript.objects.get_or_create(
            content=(
                "Diving deeper into Algebra, we tackled quadratic equations. "
                "The class learned about factoring techniques and the quadratic formula, "
                "which is essential for finding the roots of these equations."
            ),
            source='Lecture',
            related_lesson=lesson2
        )

        # Add student transcripts for the second lesson (simulating a less formal summary)
        Transcript.objects.get_or_create(
            content=(
                "Quadratic equations are tougher, but we learned a cool formula "
                "that solves them. It's something about 'b squared minus 4ac' under a square root. "
                "The teacher showed us some neat tricks to make it easier."
            ),
            source='Student',
            related_lesson=lesson2
        )

        # Create a test for the Algebra class
        Test.objects.get_or_create(
            related_class=algebra_class,
            content_area="Comprehensive test on Algebraic concepts, focused on linear and quadratic equations.",
            date=timezone.now() + timezone.timedelta(days=14),
            duration=90  # Duration in minutes
        )

        self.stdout.write(self.style.SUCCESS('Successfully populated the database with detailed data for the Algebra class.'))
