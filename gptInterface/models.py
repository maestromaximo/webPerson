from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from dotenv import load_dotenv
import os
import openai

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

    title = models.CharField(max_length=120, blank=True, null=True)

    def __str__(self):
        if self.title:
            return self.title
        else:
            self.set_title_from_messages()
            return f"ChatSession {self.id}"
    
    def get_last_message(self):
        return self.messages.last()
    
    def get_last_user_message(self):
        return self.messages.filter(is_user_message=True).last()
    
    def get_last_ai_message(self):
        return self.messages.filter(is_user_message=False).last()
    
    def get_messages(self):
        return self.messages.all()
    
    def get_messages_count(self):
        return self.messages.count()
    
    def get_user_messages_count(self):
        return self.messages.filter(is_user_message=True).count()
    
    def get_ai_messages_count(self):
        return self.messages.filter(is_user_message=False).count()
    
    def get_user_messages(self):
        return self.messages.filter(is_user_message=True)
    
    def get_ai_messages(self):
        return self.messages.filter(is_user_message=False)

    def set_title_from_messages(self):
        last_message = self.get_last_user_message()
        if last_message:
            load_dotenv()
            openai_key=os.getenv("OPENAI_API_KEY")
            openai.api_key = openai_key
            client = openai.OpenAI()

            # Create chat completion using the OpenAI API Sample response ChatCompletionMessage(content='Hello! How can I assist you today?', role='assistant', function_call=None, tool_calls=None)
            try:
                completion = client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": f"Only respond with the title, provide a title summirizing this request: \"{last_message.text}\""}
                    ]
                    )

                # Extract the assistant's response
                assistant_response = completion.choices[0].message
            except:
                assistant_response = f"chat number {self.id} - {last_message.text[:10]}"

            self.title = assistant_response.content.strip()[:120]
            self.save()
        else:
            self.title = f"ChatSession {self.id}"
            self.save()

class Message(models.Model):
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_user_message = models.BooleanField(default=True)  # True if message is from the user, False if from AI

    def __str__(self):
        return f"Message {self.id} - {('User' if self.is_user_message else 'AI')} - {self.text[:50]}"
    



### Start of Auth Models
ACCESS_LEVEL_CHOICES = [
    ('basic', 'Basic'),
    ('premium', 'Premium'),
    ('advanced', 'Advanced'),
] 

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=255, blank=True, null=True, unique=True, help_text="Username")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True, help_text="Full Name")
    email = models.EmailField(blank=True, null=True, unique=True ,help_text="Email Address")
    phone = models.IntegerField(null=True, help_text="Phone Number")

    access_level = models.CharField(max_length=50, choices=ACCESS_LEVEL_CHOICES, default='basic', help_text="Access Level")
    usage_costs = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Usage Costs")
    api_rate_hourly = models.IntegerField(default=20, help_text="API Rate Hourly")

    password = models.CharField(max_length=255, blank=True, null=True, help_text="Password")

    bio = models.TextField(blank=True, null=True, help_text="A short bio about the User [Optional]")
    
    
    

    def __str__(self):
        return f"{self.user.username}'s Profile"
