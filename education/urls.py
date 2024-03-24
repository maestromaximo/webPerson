from django.urls import path
from . import views

urlpatterns = [
    path('', views.education_home, name='education_home'),

]