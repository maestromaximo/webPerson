from django.contrib import admin
from .models import FieldEntry, Account, BudgetCategory, Budget

@admin.register(FieldEntry)
class FieldEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'message', 'money', 'category', 'type')
    list_filter = ('date', 'type', 'category', 'money')
    search_fields = ('message',)
    ordering = ('-date', '-time')

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
