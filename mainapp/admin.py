from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib import admin
from django.db.models import Sum
from .models import FieldEntry, Account, BudgetCategory, Budget, GeneralNotes, BudgetLog, Overspenditure


class GeneralNotesInline(admin.StackedInline):
    model = GeneralNotes
    extra = 1

@admin.register(FieldEntry)
class FieldEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'message', 'money', 'category', 'type')
    list_filter = ('date', 'type', 'category', 'money')
    search_fields = ('message',)
    ordering = ('-date', '-time')
    inlines = [GeneralNotesInline]

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'current_balance')

@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'weekly_limit', 'amount_spent')
    list_filter = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('name',)
    ordering = ('-start_date',)
    filter_horizontal = ('categories',)

@admin.register(BudgetLog)
class BudgetLogAdmin(admin.ModelAdmin):
    list_display = ('start_week', 'end_week', 'transportation_limit', 'food_limit', 'entertainment_limit', 'takeout_limit', 'supplies_limit')
    list_filter = ('start_week', 'end_week')
    search_fields = ('start_week', 'end_week')
    ordering = ('-start_week',)

@admin.register(GeneralNotes)
class GeneralNotesAdmin(admin.ModelAdmin):
    list_display = ('fieldEntry', 'note', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('note', 'fieldEntry__message')
    ordering = ('-created_at',)



def recalculate_overspenditure(modeladmin, request, queryset):
    start_date = datetime.now().date() - timedelta(days=30)
    end_date = datetime.now().date()

    total_budget = Decimal(0)
    total_withdrawals = FieldEntry.objects.filter(
        type='withdrawal', date__range=[start_date, end_date]
    ).aggregate(total=Sum('money'))['total'] or Decimal(0)

    last_week_expenses = Decimal(FieldEntry.objects.filter(
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('money'))['total'] or 0)

    budget = Budget.objects.first()
    if budget:
        categories = budget.categories.all()
        for cat in categories:
            total_budget += Decimal(cat.weekly_limit)

    current_balance = total_budget - Decimal(total_withdrawals)
    last_week_balance = total_budget - last_week_expenses

    overspenditure, created = Overspenditure.objects.get_or_create(defaults={'last_updated': start_date})
    
    if last_week_balance < 0:
        overspenditure.amount += Decimal(last_week_balance)
    elif last_week_balance > 0 and overspenditure.amount < 0:
        overspenditure.amount += Decimal(last_week_balance)

    overspenditure.last_updated = end_date
    overspenditure.save()

    modeladmin.message_user(request, "Overspenditure recalculated successfully.")

recalculate_overspenditure.short_description = 'Recalculate Overspenditure from 30 days ago'

@admin.register(Overspenditure)
class OverspenditureAdmin(admin.ModelAdmin):
    actions = [recalculate_overspenditure]


