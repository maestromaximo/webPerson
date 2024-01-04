from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home_food'),
    path('scanning/', views.barcode_scanning, name="barcode_scanning"),
    path('api/barcode_info/', views.barcode_info, name='barcode_info'),
    path('api/barcode_info/confirm_data/', views.confirm_data, name='confirm_data'),
    path('food_modification/', views.food_modification, name='food_modification'),
    path('meal-planner/', views.main_meal_planner, name='meal_planner_main'),
    path('meal-detail/<str:day>/', views.meal_detail, name='meal_detail'),
]
