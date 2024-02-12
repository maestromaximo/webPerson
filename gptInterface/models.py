from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class ChatModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    notes = models.TextField(blank=True)
    model_name = models.CharField(max_length=50, default='gpt-3.5-turbo-0613')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            
        super().save(*args, **kwargs)

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # If using ChatModel, consider adding a ForeignKey to link a session to a specific AI model
    ai_model = models.ForeignKey(ChatModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')

    def __str__(self):
        return f"ChatSession {self.id} - {self.user.username}"

class Message(models.Model):
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_user_message = models.BooleanField(default=True)  # True if message is from the user, False if from AI

    def __str__(self):
        return f"Message {self.id} - {('User' if self.is_user_message else 'AI')} - {self.text[:50]}"
