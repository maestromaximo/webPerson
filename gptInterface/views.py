import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# from openaiunlimitedfun import chat_context_function_bank, set_openai_api_key, manage_available_functions, manage_function_list  # Replace with the actual name of your script
from dotenv import load_dotenv
import os
import openai
from .models import ChatModel, ChatSession, Message, Profile, Documenter
from .utils import transcribe_audio_with_whisper, generate_chat_completion
from django.conf import settings

# Load environment variables from .env file
load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")
openai.api_key = openai_key
client = openai.OpenAI()

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
@login_required
def interface_menu(request):
    return render(request, 'interfaceMainMenu.html', {})

@staff_member_required
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

@staff_member_required   
@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_input = data.get('message', 'No message found')
        model_slug = data.get('model_slug', 'default-model-slug')

        session_id = data.get('session_id')
        
        try:
            chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found'}, status=404)
        
        try:
            ai_model = ChatModel.objects.get(slug=model_slug)
        except ChatModel.DoesNotExist:
            return JsonResponse({'error': 'AI model not found'}, status=404)

        # Conditional parsing of pre_messages
        try:
            pre_messages = json.loads(ai_model.pre_messages) if ai_model.pre_messages else []
        except json.JSONDecodeError:
            pre_messages = []  # Fallback to an empty list if there is a JSON format issue
        
        # Fetch recent user and assistant messages for context
        context_messages = Message.objects.filter(chat_session=chat_session).order_by('created_at')[:15]

        # Combine pre-messages with the context messages, ensuring correct ordering
        messages_for_api = pre_messages + [
            {"role": "user" if msg.is_user_message else "assistant", "content": msg.text} 
            for msg in context_messages
        ]

        # Add the latest user input to the end
        messages_for_api.append({"role": "user", "content": user_input})

        print(messages_for_api)

        # Call OpenAI API with the messages
        completion = client.chat.completions.create(
            model=ai_model.model_name,
            messages=messages_for_api
        )

        assistant_response = completion.choices[0].message
        # Save AI response to the database
        Message.objects.create(chat_session=chat_session, text=user_input, is_user_message=True)
        Message.objects.create(chat_session=chat_session, text=assistant_response.content.strip(), is_user_message=False)
        # Message.objects.create(chat_session=chat_session, text=user_input, is_user_message=True)
        # Return the assistant's response
        return JsonResponse({"response": assistant_response.content.strip()})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
@staff_member_required
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
    
@staff_member_required        
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

@staff_member_required
@login_required
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
from django.utils.text import slugify
from tqdm import tqdm
from django.contrib.auth.models import User

@csrf_exempt
def login_viewOLD(request):
    if request.method == 'POST':
        login_identifier = request.POST.get('username')  # Can be an email or username
        password = request.POST.get('password')

        # Attempt to find a profile by username or email
        try:
            if "@" in login_identifier:  # Assume it's an email
                profile = Profile.objects.get(email=login_identifier)
            else:
                # print('debugging username')
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
    
@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        login_identifier = request.POST.get('username')  # Can be an email or username
        password = request.POST.get('password')

        # Attempt to find a profile by username or email
        try:
            if "@" in login_identifier:  # Assume it's an email
                profile = User.objects.get(email=login_identifier)
            else:
                # print('debugging username')
                profile = User.objects.get(username=login_identifier)
        except Profile.DoesNotExist:
            # Here you would handle the logic to offer a signup option
            # For this example, we'll just return an error
            return JsonResponse({'error': 'Profile not found. Consider signing up?'}, status=404)

        # Authenticate the found user
        user = authenticate(request, username=login_identifier, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
            # return JsonResponse({'message': 'Login successful'})
        else:
            return redirect('login')
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    else:
        # If not POST, just show the login form (assuming you have a template named 'login.html')
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'login_page.html')
    
def logout_view(request):
    logout(request)
    return redirect('login')
    

#######################
@staff_member_required
@login_required
def documenter(request):
    if request.method == 'POST' and 'code-title' in request.POST and request.POST['code-title'].strip():
       
        title = request.POST['code-title'].strip()
        slug = slugify(title)
        documenter, created = Documenter.objects.get_or_create(title=title, defaults={'title': title, 'slug': slug})

        # Define the paths where the audio files are stored
        AUDIO_FILES_DIRECTORY = settings.AUDIO_FILES_DIRECTORY
        sections = ['runbook', 'dependencies', 'functions', 'general', 'notes']
        summaries = {}

        for section in sections:
            filepath = os.path.join(AUDIO_FILES_DIRECTORY, f"{section}.mp3")
            if os.path.exists(filepath):
                transcription = transcribe_audio_with_whisper(filepath)
                setattr(documenter, f'raw_{section}_transcript', transcription)
                os.remove(filepath)

                # Generate summaries using the raw transcript
                if section == 'functions':
                    prompt = f"Provided is a transcription of the list of functions from  script and their descriptions. Please summarize each of the functions and their purposes and return ONLY a list with the summaries of each function, do not add any other message. \n\nTranscription: {transcription}"
                elif section == 'runbook':
                    prompt = f"Provided is a transcription of how to run a specified script. Please summarize it in lenght to a runbook. \n\nTranscription: {transcription}"
                elif section == 'dependencies':
                    prompt = f"Provided is a transcription of the dependencies and or imports of a script. Please provide a simple list NOTHING ELSE where on each line you state the packages dependencies or imports nessesary for this script . \n\nTranscription: {transcription}"
                elif section == 'general':
                    prompt = f"Provided is a transcription of the general description of a script. Please summarize it in lenght to a general summary of it. \n\nTranscription: {transcription}"
                
                response = generate_chat_completion(prompt, use_gpt4=False)
                summaries[section] = response


        # Save summaries to the model
        documenter.summarized_runbook = summaries.get('runbook', '')
        documenter.summarized_dependencies = summaries.get('dependencies', '')
        documenter.general_summary = summaries.get('general', '')
        documenter.functions = summaries.get('functions', '')

        final_runbook_prompt = f"Here provided are the description of a script, its functions, dependencies and a draft short runbook. Please aggreagate all of this information to generate a long, final Runbook, write as much as possible, here is the information: \n\nGeneral Description: {documenter.general_summary}\n\nFunctions: {documenter.functions}\n\nDependencies: {documenter.summarized_dependencies}\n\nDraft runbook: {documenter.summarized_runbook}"
        final_runbook_response = generate_chat_completion(final_runbook_prompt, use_gpt4=False)
        documenter.final_runbook = final_runbook_response

        final_documentation_prompt = f"Here provided are the description of a script, its functions, dependencies, notes and a runbook. Please aggreagate all of this information to generate a long, final Documentation, write as much as possible, here is the information: \n\nGeneral Description: {documenter.general_summary}\n\nFunctions: {documenter.functions}\n\nDependencies: {documenter.summarized_dependencies}\n\nNotes: {documenter.raw_notes_transcript}\n\nRunbook: {documenter.final_runbook}"
        final_documentation_response = generate_chat_completion(final_documentation_prompt, use_gpt4=False)
        documenter.final_documentation = final_documentation_response

        documenter.save()

        context = {
            'success': True,
            'message': 'Documenter updated successfully',
        }
        return redirect('view_documenter', slug=documenter.slug)
        return render(request, 'documenter.html', context)
        # return JsonResponse({'status': 'success', 'message': 'Documenter updated successfully'}, status=200)
    elif request.method == 'POST' and 'code-title' not in request.POST:
        print('No title, no action done')
    else:
        # This will be a GET request or a POST request without a title
        context = {
            'success': False,
            'message': 'Title not provided or invalid request.' if request.method == 'POST' else '',
        }
        return render(request, 'documenter.html', context)

@staff_member_required
@login_required
@csrf_exempt
def save_audio(request):
    if request.method == 'POST':
        audio_file = request.FILES.get('audio')
        if audio_file:
            # Ensure the audio recordings directory exists
            os.makedirs(settings.AUDIO_FILES_DIRECTORY, exist_ok=True)

            # Clean title and create filename
            title = request.POST.get('title', 'untitled').replace(" ", "_")
            filename = f"{title}.mp3"

            # Full path where the audio file will be saved
            temp_audio_path = os.path.join(settings.AUDIO_FILES_DIRECTORY, filename)

            # Save the audio file
            with open(temp_audio_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            return JsonResponse({'status': 'success', 'path': temp_audio_path}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'No audio file provided'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def view_documenter(request, slug):
    documenter = get_object_or_404(Documenter, slug=slug)
    return render(request, 'view_documenter.html', {'documenter': documenter})