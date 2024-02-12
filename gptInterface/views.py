import json
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
openai.api_key = openai_key
client = openai.OpenAI()

@login_required
def interface_menu(request):

    return render(request, 'interfaceMainMenu.html', {})


@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        # Convert the request body to JSON
        data = json.loads(request.body)

        # Fetch user input from the POST request
        user_input = data.get('message', 'No message found')
        model_name = data.get('model_name', 'gpt-3.5-turbo')

        # Prepare the messages for the chat completion request
        context_messages = request.session.get('chat_context', [])
        messages = [{"role": "user", "content": message} for message in context_messages]
        messages.append({"role": "user", "content": user_input})

        print(messages)

        # Create chat completion using the OpenAI API Sample response ChatCompletionMessage(content='Hello! How can I assist you today?', role='assistant', function_call=None, tool_calls=None)
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."}
            ]+messages
            )

        # Extract the assistant's response
        assistant_response = completion.choices[0].message
        # print(assistant_response)
        assistant_message = {"role": "assistant", "content": assistant_response.content.strip()}

        # Update the chat context in the session
        user_input = {"role": "user", "content": user_input}
        updated_context = context_messages + [user_input, assistant_message]
        request.session['chat_context'] = updated_context

        return JsonResponse({'response': assistant_message['content']})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def chat(request, model=None):

    context = {

        'slug': model,

        }
    return render(request, 'chat.html')