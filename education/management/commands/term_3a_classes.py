from django.core.management.base import BaseCommand
from education.models import Class, Schedule
from django.utils.dateparse import parse_time

class Command(BaseCommand):
    help = 'Initializes classes and their schedules'

    def handle(self, *args, **options):
        class_data = [
            {"name": "Statistics 231", "subject": "STAT", "slug": "statistics-231"},
            {"name": "Mechanics 363", "subject": "PHYS", "slug": "mechanics-363"},
            {"name": "Ordinary Differential Equations 351", "subject": "AMATH", "slug": "ordinary-differential-equations-351"},
            {"name": "EM2 342", "subject": "PHYS", "slug": "em2-342"},
            {"name": "Stochastic Processes 333", "subject": "STAT", "slug": "stochastic-processes-333"},
        ]

        schedule_data = {
            "statistics-231": [
                {"day_of_week": "Monday", "start_time": "11:30", "end_time": "12:20"},
                {"day_of_week": "Wednesday", "start_time": "11:30", "end_time": "12:20"},
                {"day_of_week": "Friday", "start_time": "11:30", "end_time": "12:20"}
            ],
            "mechanics-363": [
                {"day_of_week": "Monday", "start_time": "8:30", "end_time": "9:50"},
                {"day_of_week": "Wednesday", "start_time": "8:30", "end_time": "9:50"},
                {"day_of_week": "Thursday", "start_time": "8:30", "end_time": "9:50"}
            ],
            "ordinary-differential-equations-351": [
                {"day_of_week": "Tuesday", "start_time": "10:00", "end_time": "11:20"},
                {"day_of_week": "Thursday", "start_time": "10:00", "end_time": "11:20"}
            ],
            "em2-342": [
                {"day_of_week": "Monday", "start_time": "11:30", "end_time": "12:50"},
                {"day_of_week": "Wednesday", "start_time": "11:30", "end_time": "12:50"},
                {"day_of_week": "Friday", "start_time": "11:30", "end_time": "12:50"}
            ],
            "stochastic-processes-333": [
                {"day_of_week": "Monday", "start_time": "4:00", "end_time": "5:20"},
                {"day_of_week": "Wednesday", "start_time": "4:00", "end_time": "5:20"}
            ],
        }

        for class_info in class_data:
            class_obj, created = Class.objects.get_or_create(
                name=class_info['name'],
                subject=class_info['subject'],
                defaults={'slug': class_info['slug']}  # Ensure slug is only set on creation
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created class {class_obj.name}'))

            # Create or update schedules
            for schedule_info in schedule_data.get(class_obj.slug, []):
                Schedule.objects.update_or_create(
                    class_belongs=class_obj,
                    day_of_week=schedule_info['day_of_week'],
                    start_time=parse_time(schedule_info['start_time']),
                    end_time=parse_time(schedule_info['end_time']),
                    defaults={'start_time': parse_time(schedule_info['start_time']), 'end_time': parse_time(schedule_info['end_time'])}
                )
                self.stdout.write(self.style.SUCCESS(f'Added/Updated schedule for {class_obj.name} on {schedule_info["day_of_week"]}'))
