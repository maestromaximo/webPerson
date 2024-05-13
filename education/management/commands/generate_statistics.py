import statistics
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from education.models import Transcript, Lesson
import numpy as np


class Command(BaseCommand):
    help = 'Generate statistics for transcripts and lessons'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Increase output verbosity',
        )

    def handle(self, *args, **kwargs):
        verbose = kwargs['verbose']
        
        # Statistics for Transcripts
        self.stdout.write(self.style.SUCCESS('Calculating transcript statistics...'))
        
        transcript_stats = {
            'Lecture': {'word_count': [], 'summary_word_count': []},
            'Student': {'word_count': [], 'summary_word_count': []},
        }

        transcripts = Transcript.objects.all()
        for transcript in transcripts:
            word_count = len(transcript.content.split())
            transcript_stats[transcript.source]['word_count'].append(word_count)
            
            if transcript.summarized:
                summary_word_count = len(transcript.summarized.split())
                transcript_stats[transcript.source]['summary_word_count'].append(summary_word_count)

        avg_word_count = {source: np.mean(stats['word_count']) for source, stats in transcript_stats.items()}
        avg_summary_word_count = {source: np.mean(stats['summary_word_count']) for source, stats in transcript_stats.items()}

        if verbose:
            self.stdout.write(self.style.SUCCESS(f'Average word count per transcript type: {avg_word_count}'))
            self.stdout.write(self.style.SUCCESS(f'Average summary word count per transcript type: {avg_summary_word_count}'))
        
        # Average prompt input for a lesson
        avg_prompt_input = {source: avg_summary_word_count[source] * 9 for source in avg_summary_word_count}

        if verbose:
            self.stdout.write(self.style.SUCCESS(f'Average prompt input per lesson: {avg_prompt_input}'))

        # Statistics for Lessons
        self.stdout.write(self.style.SUCCESS('Calculating lesson statistics...'))
        
        lesson_fields = [
            'interdisciplinary_connections',
            'real_world_applications',
            'creative_synthesis_of_ideas',
            'detail_level_comparison',
            'accuracy_of_information',
            'direct_concept_comparison',
            'strengths_in_students_understanding',
            'understanding_gaps',
            'comparison_of_key_concepts',
        ]
        
        lesson_stats = {field: [] for field in lesson_fields}

        lessons = Lesson.objects.all()
        for lesson in lessons:
            for field in lesson_fields:
                field_value = getattr(lesson, field)
                if field_value:
                    lesson_stats[field].append(len(field_value.split()))

        avg_lesson_output = {field: np.mean(stats) for field, stats in lesson_stats.items() if stats}

        if verbose:
            self.stdout.write(self.style.SUCCESS(f'Average word count per lesson field: {avg_lesson_output}'))

        # Additional statistics
        additional_stats = {}
        for field, stats in lesson_stats.items():
            if stats:
                additional_stats[field] = {
                    'median': np.median(stats),
                    'mode': statistics.mode(stats),
                    'variance': np.var(stats),
                    'covariance': np.cov(stats)
                }

        if verbose:
            self.stdout.write(self.style.SUCCESS(f'Additional statistics per lesson field: {additional_stats}'))

        self.stdout.write(self.style.SUCCESS('Statistics generated successfully!'))

        # Output results
        self.stdout.write(self.style.SUCCESS('--- Transcript Statistics ---'))
        self.stdout.write(self.style.SUCCESS(f'Average word count per transcript type: {avg_word_count}'))
        self.stdout.write(self.style.SUCCESS(f'Average summary word count per transcript type: {avg_summary_word_count}'))
        self.stdout.write(self.style.SUCCESS(f'Average prompt input per lesson: {avg_prompt_input}'))

        self.stdout.write(self.style.SUCCESS('--- Lesson Statistics ---'))
        self.stdout.write(self.style.SUCCESS(f'Average word count per lesson field: {avg_lesson_output}'))
        self.stdout.write(self.style.SUCCESS(f'Additional statistics per lesson field: {additional_stats}'))
