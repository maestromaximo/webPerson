from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta

def home(request):
    

    return render(request, 'homeFood.html')

def barcode_scanning(request):
    return render(request, 'scanning_page.html')