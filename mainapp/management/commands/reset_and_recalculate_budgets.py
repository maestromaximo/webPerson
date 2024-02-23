from django.core.management.base import BaseCommand
from mainapp.models import BudgetCategory, FieldEntry
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Resets budget categories to zero and recalculates based on this week\'s field entries'

    def handle(self, *args, **kwargs):
        # Reset all BudgetCategory amounts to zero
        BudgetCategory.objects.update(amount_spent=0)

        # Calculate the start of the current week
        today = datetime.today().date()
        start_of_week = today - timedelta(days=today.weekday())

        # Filter FieldEntry objects from the start of this week
        this_week_entries = FieldEntry.objects.filter(date__gte=start_of_week)

        # Recalculate the amounts
        for entry in this_week_entries:
            if entry.category:  # Check if entry.category is not None
                try:
                    budget_category = BudgetCategory.objects.filter(name__icontains=entry.category).first()
                    if budget_category:
                        budget_category.amount_spent += entry.money
                        budget_category.save()
                    else:
                        print(f'Missed category for entry: {entry}')
                except BudgetCategory.DoesNotExist:
                    print('Missed category!!')
                    pass
            else:
                print(f'Entry without category: {entry}')

        self.stdout.write(self.style.SUCCESS('Successfully reset and recalculated budget categories'))
