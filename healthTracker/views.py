from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, requests
from datetime import datetime, timedelta
from .models import FoodItem, Meal
from .utils import meal_recipe_creator
import os

def home(request):
    

    return render(request, 'homeFood.html')

def barcode_scanning(request):
    return render(request, 'scanning_page.html')

@csrf_exempt
def barcode_info(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        barcode = data.get('barcode')

        # Query the Open Food Facts API
        api_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(api_url)
        if response.status_code == 200:
            product_data = response.json().get('product', {})
            product_name = product_data.get('product_name', 'Product name not available')
            nutritional_info = product_data.get('nutriments', {})

            response_data = {
                'barcode': barcode,
                'product_name': product_name,
                'nutritional_info': nutritional_info
            }
        else:
            response_data = {
                'barcode': barcode,
                'error': 'Product not found or API error'
            }

        return JsonResponse(response_data)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

@csrf_exempt
def confirm_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_name = data.get('product_name', 'Unknown Product')
        nutritional_info = data.get('nutritional_info', {})
        # print(data)
        # Create a string representation of nutritional values
        nutritional_values_str = json.dumps(nutritional_info)

        # Extract specific nutritional values
        calories = nutritional_info.get('energy-kcal_100g', 0)
        fat = nutritional_info.get('fat_100g', 0)
        protein = nutritional_info.get('proteins_100g', 0)
        carbohydrates = nutritional_info.get('carbohydrates_100g', 0)
        sugars = nutritional_info.get('sugars_100g', 0)
        sodium = nutritional_info.get('sodium_100g', 0)

        # Create FoodItem object
        food_item = FoodItem.objects.create(
            name=product_name,
            nutritional_values=nutritional_values_str,
            purchased_date=datetime.today(),
            calories=calories,
            fat=fat,
            protein=protein,
            carbohydrates=carbohydrates,
            sugars=sugars,
            sodium=sodium
        )
        # return redirect('food_modification')
        return JsonResponse({'status': 'success', 'message': 'Food item saved'})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    


def food_modification(request):
    if request.method == 'POST':
        # Parsing form data
        name = request.POST.get('name')
        image = request.FILES.get('image')  # Assuming image upload is handled in the form
        nutritional_values = request.POST.get('nutritional_values')
        expiration_date = request.POST.get('expiration_date')
        weight = request.POST.get('weight')
        quantity_per_package = request.POST.get('quantity_per_package')
        calories = request.POST.get('calories')
        fat = request.POST.get('fat')
        protein = request.POST.get('protein')
        carbohydrates = request.POST.get('carbohydrates')
        sugars = request.POST.get('sugars')
        sodium = request.POST.get('sodium')

        # Create or update FoodItem
        food_item, created = FoodItem.objects.update_or_create(
            name=name,
            defaults={
                'image': image,
                'nutritional_values': nutritional_values,
                'expiration_date': datetime.strptime(expiration_date, '%Y-%m-%d') if expiration_date else None,
                'weight': weight,
                'quantity_per_package': quantity_per_package,
                'calories': calories,
                'fat': fat,
                'protein': protein,
                'carbohydrates': carbohydrates,
                'sugars': sugars,
                'sodium': sodium
            }
        )

        return redirect('barcode_scanning')  # Redirect to the scanning page

    else:
        # Display the form for the most recent FoodItem
        food_item = FoodItem.objects.last()  # Get the most recent FoodItem
        return render(request, 'food_modification.html', {'food_item': food_item})
    
def main_meal_planner(request):
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday

    # Fetch available food items
    # Note: Adjust the filter logic based on how you determine the availability
    available_food_items = FoodItem.objects.filter(purchased_date__gte=start_of_week, expiration_date__lte=end_of_week)

    context = {
        'week_days': [start_of_week + timedelta(days=i) for i in range(7)],
        'available_food_items': available_food_items,
    }
    return render(request, 'meal_planner_main.html', context)