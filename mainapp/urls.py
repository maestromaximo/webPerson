from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/purchase_made', views.purchase_made_endpoint, name='api_purchase_made'),
]
