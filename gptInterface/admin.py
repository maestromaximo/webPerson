from django.contrib import admin
from .models import ChatModel

@admin.register(ChatModel)
class ChatModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'model_name')
    prepopulated_fields = {'slug': ('name',)}
