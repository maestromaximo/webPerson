from django.urls import path
from . import views

urlpatterns = [
    path('', views.interface_menu, name='interface_menu'),


]