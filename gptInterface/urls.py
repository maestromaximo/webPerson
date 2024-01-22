from django.urls import path
from . import views

urlpatterns = [
    path('', views.interface_menu, name='interface_menu'),
    # path('chat/', views.chat, name='chat'),
    path('chat/', views.chat_view, name='chat_view'),
    path('chat/<slug:model>', views.chat, name='chat'),
]