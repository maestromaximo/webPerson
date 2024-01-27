from django.contrib import admin
from .models import FieldEntry, Account, BudgetCategory, Budget, GeneralNotes, BudgetLog


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


