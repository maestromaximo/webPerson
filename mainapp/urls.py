from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/purchase_made', views.purchase_made_endpoint, name='api_purchase_made'),
    path('classification/', views.classification_menu, name="classification_menu"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('budget/', views.budget, name='budget'),
    path('budget/update/', views.update_budget, name='update_budget'),
    path('chat/', views.chat_interface, name='chat_interface'),
    path('chat/api/', views.chat_with_agent, name='chat_with_agent'),

    path('privacy/', views.privacy, name='privacy'),

]
