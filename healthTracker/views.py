from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, requests
from datetime import datetime, timedelta

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