import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# from openaiunlimitedfun import chat_context_function_bank, set_openai_api_key, manage_available_functions, manage_function_list  # Replace with the actual name of your script
from dotenv import load_dotenv
import os
import openai
from .models import ChatModel, ChatSession, Message, Profile

# Load environment variables from .env file
load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")
openai.api_key = openai_key
client = openai.OpenAI()

@login_required
def interface_menu(request):

    return render(request, 'interfaceMainMenu.html', {})


@csrf_exempt
def chat_viewDEPRECATED(request):
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
    
@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_input = data.get('message', 'No message found')
        model_slug = data.get('model_slug', 'default-model-slug')  # This should be passed from the frontend

        session_id = data.get('session_id')  # Expect session_id to be passed with the request
        
        try:
            chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found'}, status=404)
        
        try:
            ai_model = ChatModel.objects.get(slug=model_slug)
        except ChatModel.DoesNotExist:
            return JsonResponse({'error': 'AI model not found'}, status=404)

        # Fetch or create a ChatSession for the current user
        # chat_session, _ = ChatSession.objects.get_or_create(user=request.user)

        # Fetch or create the ChatModel based on the slug
        ai_model, _ = ChatModel.objects.get_or_create(slug=model_slug)

        # Update the chat session with the selected AI model
        chat_session.ai_model = ai_model
        chat_session.save()

        # Save user message to the database
        user_message = Message.objects.create(chat_session=chat_session, text=user_input, is_user_message=True)
        

        # Fetch recent messages for context (consider limiting the number of messages for performance)
        context_messages = Message.objects.filter(chat_session=chat_session).order_by('created_at')[:15]

        # Prepare messages for the OpenAI completion request
        messages_for_api = [{"role": "system", "content": "You are a helpful assistant."}]
        messages_for_api += [{"role": "user" if msg.is_user_message else "assistant", "content": msg.text} for msg in context_messages]

        print(messages_for_api)

        # Call OpenAI API with the messages
        completion = client.chat.completions.create(
            model=ai_model.model_name,
            messages=messages_for_api
        )

        assistant_response = completion.choices[0].message
        # Save AI response to the database
        Message.objects.create(chat_session=chat_session, text=assistant_response.content.strip(), is_user_message=False)

        # Return the assistant's response
        return JsonResponse({'response': assistant_response.content.strip()})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

@csrf_exempt
@login_required
def chat_viewddd(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_input = data.get('message', '')
        model_slug = data.get('model_slug', 'default-model-slug')

        # Extract session_id, ensure it's passed and valid
        session_id = data.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)

        # Attempt to fetch the chat session
        try:
            chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found'}, status=404)
        
        # Attempt to fetch the AI model
        try:
            ai_model = ChatModel.objects.get(slug=model_slug)
        except ChatModel.DoesNotExist:
            return JsonResponse({'error': 'AI model not found'}, status=404)

        # Save user message to the database
        Message.objects.create(chat_session=chat_session, text=user_input, is_user_message=True)
        
        # Optionally, fetch recent messages for context (not shown here for brevity)
        # context_messages = Message.objects.filter(chat_session=chat_session).order_by('-created_at')[:15]

        # Call OpenAI API with the message (simplified for demonstration)
        try:
            response = openai.ChatCompletion.create(
                model=ai_model.model_name,  # Use the model name from your ChatModel instance
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_input}
                ]
            )
            assistant_response = response.choices[0].message.content.strip()
        except Exception as e:
            return JsonResponse({'error': 'OpenAI API error: {}'.format(str(e))}, status=500)

        # Save AI response to the database
        Message.objects.create(chat_session=chat_session, text=assistant_response, is_user_message=False)

        # Return the assistant's response
        return JsonResponse({'response': assistant_response})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
        
@csrf_exempt
def fetch_session_messages(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=403)
    
    try:
        chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        # print(chat_session)
        messages = Message.objects.filter(chat_session=chat_session).order_by('created_at')
        messages_data = [{'text': message.text, 'is_user_message': message.is_user_message} for message in messages]
        return JsonResponse({'messages': messages_data})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Chat session not found'}, status=404)


# @login_required
def chat(request, model=None):
    # Delete empty chat sessions for the current user

    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        # Handle the case where the user does not have a profile
        # For example, redirect to a profile creation page or show an error message
        # Here we'll simply log them out and redirect to the login page for simplicity
        return redirect('login')

    ChatSession.objects.filter(user=request.user, messages__isnull=True).delete()

    # Automatically create a new chat session for each visit to the chat page
    new_session = ChatSession.objects.create(user=request.user)
    
    ai_models = ChatModel.objects.all()  # Fetch all ChatModel instances
    chat_sessions = ChatSession.objects.filter(user=request.user).exclude(id=new_session.id)  # Exclude the current session
    
    context = {
        'ai_models': ai_models,
        'current_session_id': new_session.id,  # Pass the current session ID to the template
        'chat_sessions': chat_sessions,  # Pass previous sessions to the template for history
    }
    return render(request, 'chat.html', context)



##Auth views

from django.contrib.auth import login, authenticate
from django.contrib.auth import logout

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        login_identifier = request.POST.get('username')  # Can be an email or username
        password = request.POST.get('password')

        # Attempt to find a profile by username or email
        try:
            if "@" in login_identifier:  # Assume it's an email
                profile = Profile.objects.get(email=login_identifier)
            else:
                profile = Profile.objects.get(username=login_identifier)
        except Profile.DoesNotExist:
            # Here you would handle the logic to offer a signup option
            # For this example, we'll just return an error
            return JsonResponse({'error': 'Profile not found. Consider signing up?'}, status=404)

        # Authenticate the found user
        user = authenticate(request, username=profile.user.username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'message': 'Login successful'})
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    else:
        # If not POST, just show the login form (assuming you have a template named 'login.html')
        return render(request, 'login_page.html')
    
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'message': 'Logout successful'})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
