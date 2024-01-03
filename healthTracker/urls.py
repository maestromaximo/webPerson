from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home_food'),
    path('scanning/', views.barcode_scanning, name="barcode_scanning"),
]
