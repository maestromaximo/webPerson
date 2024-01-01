from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import FieldEntry
import json
from datetime import datetime


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