from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import FieldEntry
import json
from datetime import datetime
from .utils import classify_transaction_simple

def home(request):
    return render(request, 'home.html')

@csrf_exempt  # Disable CSRF for this view
def purchase_made_endpoint(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            entry = FieldEntry.objects.create(
                date=datetime.strptime(data['date'], "%Y-%m-%d").date(),
                time=datetime.strptime(data['time'], "%H:%M:%S").time(),
                message=data['message'],
                money=data['amount'],
                read_status=False 
            )
            entry.save()
            return JsonResponse({'status': 'success', 'message': 'Entry saved'})
        except Exception as e:
            print(e)
            return JsonResponse({'status': 'error', 'message': 'Error processing request'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    

def classification_menu(request):
    if request.method == 'POST':
        entries = FieldEntry.objects.filter(category__isnull=True)
        for entry in entries:
            category = classify_transaction_simple(entry)
            entry.category = category
            entry.save()
        return redirect('classification_menu')  # Redirect to avoid re-posting on refresh

    total_field_entries = FieldEntry.objects.count()
    total_categorized = FieldEntry.objects.exclude(category__isnull=True).count()
    total_uncategorized = FieldEntry.objects.filter(category__isnull=True).count()

    context = {
        'total_field_entries': total_field_entries,
        'total_categorized': total_categorized,
        'total_uncategorized': total_uncategorized
    }
    return render(request, 'classification_main.html', context)

def dashboard(request):
    context = {

    }
    
    return render(request, 'dashboard.html', context)