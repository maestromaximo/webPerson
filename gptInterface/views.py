from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from openaiunlimitedfun import chat_context_function_bank, set_openai_api_key, manage_available_functions, manage_function_list  # Replace with the actual name of your script
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")
# print(openai_key)
# set_openai_api_key(api_key=openai_key)
# To save current module's functions
manage_available_functions(retrieve=False)

# To retrieve available functions
functions = manage_available_functions()
function_list = manage_function_list(retrieve=True)
# Create your views here.
@login_required
def interface_menu(request):

    return render(request, 'interfaceMainMenu.html', {})

@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        user_input = request.POST.get('message')
        context = request.session.get('chat_context', [])
        model_name = request.POST.get('model_name', 'gpt-3.5-turbo-0613')

        response, updated_context = chat_context_function_bank(question=user_input, context=context)

        # Save the updated context in the session
        request.session['chat_context'] = updated_context

        return JsonResponse({'response': response})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def chat(request, model=None):

    context = {

        'slug': model,

        }
    return render(request, 'chat.html')