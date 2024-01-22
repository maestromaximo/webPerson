from django.core.management.base import BaseCommand
from mainapp.models import BudgetCategory, FieldEntry
from datetime import datetime, timedelta
import random

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

        # Redistribution logic
        overspent_categories = BudgetCategory.objects.filter(amount_spent__gt=F('weekly_limit'))
        eligible_categories = BudgetCategory.objects.filter(amount_spent__lt=F('weekly_limit'))

        for category in overspent_categories:
            overspent_amount = category.amount_spent - category.weekly_limit
            category.amount_spent = category.weekly_limit
            category.save()

            while overspent_amount > 0 and eligible_categories.exists():
                eligible_categories_list = list(eligible_categories)
                if eligible_categories_list:
                    recipient_category = random.choice(eligible_categories_list)

                    available_space = recipient_category.weekly_limit - recipient_category.amount_spent
                    redistribution_amount = min(overspent_amount, available_space)

                    recipient_category.amount_spent += redistribution_amount
                    overspent_amount -= redistribution_amount

                    if recipient_category.amount_spent >= recipient_category.weekly_limit:
                        eligible_categories = eligible_categories.exclude(id=recipient_category.id)

                    recipient_category.save()
                else:
                    # Handling Overspent category
                    overspent_category, created = BudgetCategory.objects.get_or_create(
                        name='Overspent',
                        defaults={'weekly_limit': 150}
                    )
                    overspent_category.amount_spent += overspent_amount
                    overspent_amount = 0
                    overspent_category.save()

        self.stdout.write(self.style.SUCCESS('Successfully reset and recalculated budget categories'))
