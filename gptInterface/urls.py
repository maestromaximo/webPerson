from django.urls import path
from . import views

urlpatterns = [
    path('', views.interface_menu, name='interface_menu'),
    # path('chat/', views.chat, name='chat'),
    path('chat/', views.chat_view, name='chat_view'),
    path('chat/<slug:model>', views.chat, name='chat'),

    path('fetch-messages/<int:session_id>/', views.fetch_session_messages, name='fetch_session_messages'),
]