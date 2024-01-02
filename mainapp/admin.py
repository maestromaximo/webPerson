from django.contrib import admin
from .models import FieldEntry

@admin.register(FieldEntry)
class FieldEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'message', 'money', 'read_status', 'type')
    list_filter = ('date', 'type', 'money')
    search_fields = ('message',)
    ordering = ('-date', '-time')
