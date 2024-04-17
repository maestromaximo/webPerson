from django.contrib import admin
from .models import ChatModel, ChatSession, Documenter, Message, Profile

# Already defined ChatModelAdmin
@admin.register(ChatModel)
class ChatModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'model_name')
    prepopulated_fields = {'slug': ('name',)}


class MessageInline(admin.TabularInline):
    model = Message
    fields = ('text', 'created_at', 'is_user_message')
    readonly_fields = ('created_at',)
    extra = 0  # Number of empty forms to display
    can_delete = True  # Allows deletion of messages directly from the chat session page
    show_change_link = True  # Adds a link to the individual message's admin page

# Adjust ChatSessionAdmin to include the inline
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'ai_model')
    list_select_related = ('user', 'ai_model')
    list_filter = ('created_at', 'updated_at', 'ai_model')
    search_fields = ('user__username', 'ai_model__name')
    inlines = [MessageInline]  # Add the inline here

# Define MessageAdmin
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat_session', 'text_preview', 'created_at', 'is_user_message')
    list_select_related = ('chat_session',)
    list_filter = ('created_at', 'is_user_message', 'chat_session')
    search_fields = ('text', 'chat_session__user__username')

    def text_preview(self, obj):
        """Create a shortened preview of the message text."""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Preview'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'username', 'name', 'email', 'phone', 'access_level', 'usage_costs', 'api_rate_hourly', 'bio')
    list_filter = ('access_level',)
    search_fields = ('user__username', 'username', 'name', 'email')
    ordering = ('user', 'access_level')
    fieldsets = (
        (None, {
            'fields': ('user', 'profile_picture', 'username', 'name', 'email', 'phone', 'access_level', 'usage_costs', 'api_rate_hourly', 'password', 'bio'),
        }),
    )



@admin.register(Documenter)
class DocumenterAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('General Information', {
            'fields': ('title', 'slug', 'created_at', 'updated_at')
        }),
        ('Transcripts', {
            'fields': (
                'raw_general_transcript',
                'raw_functions_transcript',
                'raw_notes_transcript',
                'raw_runbook_transcript',
                'raw_dependencies_transcript',
            )
        }),
        ('Summaries', {
            'fields': (
                'summarized_runbook',
                'summarized_dependencies',
                'general_summary',
            )
        }),
        ('Final Documents', {
            'fields': ('final_runbook', 'final_documentation')
        }),
        ('JSON Data', {
            'fields': ('functions',),
            # 'classes': ('collapse',)  # This will make the JSON field collapsible
        }),
    )
