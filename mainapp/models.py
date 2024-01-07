from django.db import models
from django.db.models import Sum
# Create your models here.

class FieldEntry(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    date = models.DateField()
    time = models.TimeField()
    message = models.TextField()
    money = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        default='withdrawal',
    )
    category = models.CharField(max_length=40, null=True, blank=True)
    read_status = models.BooleanField(default=False)
    accounted_for = models.BooleanField(default=False)


class Account(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    total_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    weekly_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    weekly_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Additional fields for further statistics can be added here

    def update_statistics(self):
        # Assuming all FieldEntry instances relate to this account
        self.total_deposits = FieldEntry.objects.filter(type='deposit').aggregate(Sum('money'))['money__sum'] or 0
        self.total_withdrawals = FieldEntry.objects.filter(type='withdrawal').aggregate(Sum('money'))['money__sum'] or 0
        self.current_balance = self.total_deposits - self.total_withdrawals
        self.save()

    def reset_budgets(self):
        for category in BudgetCategory.objects.all():
            category.amount_spent = 0
            category.save()

    def __str__(self):
        return f"{self.name} Account: Balance, {self.current_balance}"

class BudgetCategory(models.Model):
    CATEGORY_CHOICES = [
        ('transportation', 'Transportation'),
        ('food', 'Food'),
        ('entertainment', 'Entertainment'),
        ('takeout', 'Takeout'),
        ('supplies', 'Supplies'),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES,unique=True, null=False)
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekly_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    bar_color = models.CharField(max_length=50, default="bg-blue-600")

    def __str__(self):
        return f"{self.get_name_display()} - Weekly Limit: {self.weekly_limit}"
    
class Budget(models.Model):
    name = models.CharField(max_length=100)
    categories = models.ManyToManyField(BudgetCategory)
    start_date = models.DateField()
    end_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)



    def __str__(self):
        return f"Budget: {self.name} ({self.start_date} to {self.end_date})"
    
class BudgetLog(models.Model):
    start_week = models.DateTimeField(null=True, blank=True)
    end_week = models.DateTimeField(null=True, blank=True)
    transportation_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transportation_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entertainment_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entertainment_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    takeout_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    takeout_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplies_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplies_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Budget Log ({self.start_week.strftime('%Y-%m-%d')} to {self.end_week.strftime('%Y-%m-%d')})" if self.start_week and self.end_week else "Budget Log"


