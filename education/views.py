from django.shortcuts import render

# Create your views here.

def education_home(request):
    context = {}
    return render(request, 'education/education_home.html', context)
