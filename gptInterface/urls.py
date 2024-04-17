from django.urls import path
from . import views

urlpatterns = [
    path('', views.interface_menu, name='interface_menu'),
    # path('chat/', views.chat, name='chat'),
    path('chat/', views.chat_view, name='chat_view'),
    path('chat/<slug:model>', views.chat, name='chat'),

    path('documenter/', views.documenter, name='documenter'),
    path('documenter/<slug:slug>/', views.view_documenter, name='view_documenter'),
    path('documenter/save-audio/', views.save_audio, name='save_audio'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('fetch-messages/<int:session_id>/', views.fetch_session_messages, name='fetch_session_messages'),
]