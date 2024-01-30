from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from collections import defaultdict
from mainapp.models import FieldEntry

class Command(BaseCommand):
    help = 'Lists monthly subscriptions and their totals'

    def handle(self, *args, **kwargs):
        three_months_ago = datetime.now() - timedelta(days=90)

        entries = FieldEntry.objects.filter(
            date__gte=three_months_ago,
            type='withdrawal'
        )

        # Group entries by message and amount
        grouped_entries = defaultdict(lambda: defaultdict(int))
        for entry in entries:
            grouped_entries[(entry.message, entry.money)][entry.date.month] += 1

        # Identify potential subscriptions
        subscriptions = []
        for (message, amount), month_counts in grouped_entries.items():
            if len(month_counts) >= 2 and all(count == 1 for count in month_counts.values()):
                subscriptions.append({'name': message, 'amount': amount})

        # Display results
        self.stdout.write(self.style.SUCCESS('Potential Monthly Subscriptions:'))
        for sub in subscriptions:
            self.stdout.write(f"{sub['name']}: {sub['amount']}")

        total_subscription_amount = sum(sub['amount'] for sub in subscriptions)
        self.stdout.write(self.style.SUCCESS(f"Total Estimated Subscription Amount: {total_subscription_amount}"))

