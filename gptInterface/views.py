from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# from openaiunlimitedfun import chat_context_function_bank, set_openai_api_key, manage_available_functions, manage_function_list  # Replace with the actual name of your script
from dotenv import load_dotenv
import os
import openai

# Load environment variables from .env file
load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")

@login_required
def interface_menu(request):

    return render(request, 'interfaceMainMenu.html', {})


@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        # Fetch user input from the POST request
        user_input = request.POST.get('message')
        model_name = request.POST.get('model_name', 'gpt-3.5-turbo')

        # Prepare the messages for the chat completion request
        context_messages = request.session.get('chat_context', [])
        messages = [{"role": "user", "content": message} for message in context_messages]
        messages.append({"role": "user", "content": user_input})

        # Create chat completion using the OpenAI API
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            temperature=0.7
        )

        # Extract the assistant's response
        assistant_response = response.choices[0].message['content']

        # Update the chat context in the session
        updated_context = context_messages + [user_input, assistant_response.strip()]
        request.session['chat_context'] = updated_context

        return JsonResponse({'response': assistant_response.strip()})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def chat(request, model=None):

    context = {

        'slug': model,

        }
    return render(request, 'chat.html')