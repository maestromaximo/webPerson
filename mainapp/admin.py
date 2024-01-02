from django.contrib import admin
from .models import FieldEntry

@admin.register(FieldEntry)
class FieldEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'money', 'read_status')
    list_filter = ('read_status', 'date')
    search_fields = ('message',)
    ordering = ('-date', '-time')
