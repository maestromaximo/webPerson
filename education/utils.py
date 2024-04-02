import PyPDF2
import os
from dotenv import load_dotenv
import openai
import json
import subprocess

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
# openai.api_key = 'your-api-key'
client = openai.Client()

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file and return it as a string.
    """
    text = ""
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

MODELS = {
    'gpt-4': 'gpt-4-turbo-preview',
    'gpt-4-vision': 'gpt-4-vision-preview',
    'gpt-3.5': 'gpt-3.5-turbo',
    'dall-e-3': 'dall-e-3',
    'dall-e-2': 'dall-e-2',
    'tts': 'tts-1',
    'tts-hd': 'tts-1-hd',
    'whisper': 'whisper-1',
    'text-embedding': 'text-embedding-3-large',
    'text-embedding-small': 'text-embedding-3-small',
    'moderation': 'text-moderation-latest',
}


def run_function(function_name, arguments):

    if function_name == 'run_python_code':
        return run_python_code(**arguments)
    elif function_name.endswith('pdo'):
        return arguments
    # Get all the functions defined in the same file
    functions = [obj for name, obj in globals().items() if callable(obj) and name != 'run_function']
    
    # Search for a matching function
    for function in functions:
        if function.__name__ == function_name:
            # Call the matching function with the provided arguments
            return function(**arguments)
    
    # If no matching function is found, return "No tool response"
    return "No tool response"


def run_python_code(code, filename="script.py"):
    """
    Write the given Python code to a file and execute it.
    :param code: Python code to be written and executed.
    :param filename: Name of the file where the code will be written.
    :return: Output from the executed Python script.
    """
    # Define the full path for the script, relative to this file's location
    folder_name = 'ai_tools'
    folder_dir = os.path.join(os.path.dirname(__file__),folder_name)
    script_path = os.path.join(folder_dir ,filename)

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_dir):
        os.makedirs(folder_dir)
    
    # Write the Python code to the file
    with open(script_path, 'w', encoding='utf-8') as file:
        file.write(code)
    
    # Execute the Python script and capture the output
    try:
        result = subprocess.run(['python', script_path], text=True, capture_output=True, check=True)
        output = result.stdout
        print('output:', output)
    except subprocess.CalledProcessError as e:
        output = e.output  # Get the error output if the script fails
    
    # Optionally, clean up by removing the script file after execution
    # os.remove(script_path)
    
    return output


def query_openai_with_tools(query, context=None, model="gpt-3.5-turbo", force_tool=None, tools_list=[]):
    """
    Send a query to OpenAI's API with optional function calls using the updated client object.

    :param query: The user's query or message.
    :param context: List of previous messages in the conversation for context.
    :param force_tool: Optionally force a specific tool call.
    :param tools_list: List of tool schemas to be used by the API.
    :return: The response from the OpenAI API and the new context.
    """
    # Default context if none provided
    if context is None:
        context = [{"role": "system", "content": "You are a helpful assistant."}]
    messages = context + [{"role": "user", "content": query}]
    
    # Preparing API call parameters
    api_call_params = {
        "model": model,
        "messages": messages
    }
    # Only add the 'tools' parameter if tools_list is not empty
    if tools_list:
        # print('tools_list:', tools_list)
        api_call_params["tools"] = tools_list
        if force_tool:
            api_call_params["force_tool"] = force_tool # Optionally force a specific tool call
        else:
            api_call_params["tool_choice"] = "auto" # Use the API's default tool choice algorithm
    
    # Calling the API using the client object
    # print('api_call_params:', api_call_params)
    response = client.chat.completions.create(**api_call_params)
    
    # Extracting and handling tool calls if they exist
    response_message = response.choices[0].message
    # print('response_message:', response_message)
    # sample response_message: ChatCompletionMessage(content="Hello! I'm just a computer program, so I don't have feelings, but I'm here and ready to help you with anything you need. How can I assist you today?", role='assistant', function_call=None, tool_calls=None)
    new_context = context + [response_message]  # Update context with the assistant's reply
    if response_message.tool_calls:
        # Process each tool call
        for tool_call in response_message.tool_calls:
            # print('tool_call:', tool_call)
            # sample tool_call: ChatCompletionMessageToolCall(id='call_k9QxeNbcAciKpOEqq6wqMOmz', function=Function(arguments='{"location":"Tokyo","unit":"celsius"}', name='get_current_weather'), type='function')
            function_name = tool_call.function.name  # Access the function name correctly
            function_args = json.loads(tool_call.function.arguments)  # Access the function arguments correctly
            
            # Run the specified function and get the response
            function_response = run_function(function_name, function_args)
            
            # Append the function response to the new context
            new_context.append({
                "tool_call_id": tool_call.id,  # Access the tool call ID correctly
                "role": "tool",
                "name": function_name,
                "content": function_response,
            })
        
        # Make another API call to continue the conversation with the updated context
        second_response = client.chat.completions.create(
            model=model,
            messages=new_context,  # Avoid initiating new tool calls
        )
        final_response = second_response.choices[0].message
        new_context += [final_response]  # Update the context with the final response
    else:
        # If no tool calls, use the first response as the final response
        final_response = response_message
    
    return final_response.content, new_context

# test_tool = [
#         {
#         "type": "function",
#         "function": {
#             "name": "run_python_code",
#             "description": "Execute a Python script with the provided code.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "code": {
#                         "type": "string",
#                         "description": "The Python code to execute.",
#                     },
#                     "filename": {
#                         "type": "string",
#                         "description": "Filename to save the Python code as.",
#                         "default": "script.py"
#                     }
#                 },
#                 "required": ["code"]
#             }
#         }
#     }
#     ]

# def conversation():
#     # Start a while true loop to keep the conversation going using the query_openai_with_tools function and test_tool given
#     context = None
#     while True:
#         user_input = input("You: ")
#         response, context = query_openai_with_tools(user_input, context=context, tools_list=test_tool)
#         print("AI: ", response)
