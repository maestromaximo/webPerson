import PyPDF2
import os
from dotenv import load_dotenv
import openai
import json
import subprocess
import fitz  # PyMuPDF
import re

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

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
# openai.api_key = 'your-api-key'
client = openai.Client()


def extract_toc_text(pdf_path, start_page=0, end_page=5):
    """Extracts text from the table of contents pages."""
    toc_text = ""
    with fitz.open(pdf_path) as doc:
        for page_num in range(start_page, min(end_page, len(doc))):
            page = doc.load_page(page_num)
            toc_text += page.get_text()

    return toc_text

def parse_tocV2(toc_text):
    """Parses the raw ToC text into a dictionary of chapter titles and page numbers."""
    toc_dict = {}
    lines = toc_text.split('\n')
    for line in lines:
        if '\t' in line:  # Assuming a tab character separates chapter titles from page numbers
            parts = line.rsplit('\t', 1)  # Split on the last tab character
            if len(parts) == 2:
                title, page = parts
                toc_dict[title.strip()] = page.strip()
    return toc_dict

def parse_tocV3(raw_text):
    toc_dict = {}
    lines = raw_text.strip().split('\n')
    
    for line in lines:
        # Identify lines ending with a page number: optional spaces, optional periods, mandatory number
        if re.search(r'[\s.]*\d+\s*$', line):
            # Separate title from page number
            match = re.search(r'(.+?)[\s.]+(\d+)\s*$', line)
            if match:
                title = match.group(1).strip()
                page = match.group(2).strip()
                
                # Populate the dictionary: title -> page
                toc_dict[title] = page
    
    return toc_dict

def parse_toc(raw_text):
    toc_dict = {}
    start_parsing = False
    chapter_pattern = re.compile(r'^(\d+(\.\d+)*)\s+(.*?)\s+(\d+)$')

    lines = raw_text.strip().split('\n')

    for line in lines:
        # Start parsing after "Contents" heading or similar logic
        if 'Contents' in line:
            start_parsing = True
            continue
        
        if start_parsing:
            # This pattern is designed to capture: chapter number, title, page number
            # Adjusted to ignore lines without this pattern
            match = chapter_pattern.search(line)
            if match:
                chapter_num = match.group(1).strip()
                title = match.group(3).strip()
                page = match.group(4).strip()

                # Creating a structured key: "ChapterNum: Chapter Title"
                key = f"{chapter_num}: {title}"
                toc_dict[key] = page

    return toc_dict



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

def extract_text_by_page(pdf_path, page_number):
    """Extract text from a specific page of the PDF file."""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        if page_number < len(reader.pages):
            page = reader.pages[page_number]
            return page.extract_text()
        else:
            return None
        

def find_first_toc_page(pdf_path, max_pages=20, separators=['-', '.', '\s', '*'], skip_from_page=1, continuous=True):
    """Finds pages containing title-page pairs and can continue extracting based on the continuous flag."""
    separator_pattern = "[" + "".join(separators) + "]+"
    regex_pattern = rf'(.+?){separator_pattern}(\d+)$'
    toc_dict = {}  # Initializing the dictionary to store ToC entries
    num_pages = len(PyPDF2.PdfReader(pdf_path).pages)
    end_page = min(num_pages, max_pages)
    consecutive_non_matches = 0
    found_matches = False

    for page_number in range(skip_from_page - 1, end_page):
        text = extract_text_by_page(pdf_path, page_number)
        if text:
            matches_on_page = False
            for line in text.split('\n'):
                match = re.search(regex_pattern, line, re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                    page = int(match.group(2))
                    toc_dict[title] = page
                    matches_on_page = True
                    found_matches = True  # Flag to indicate we found at least one match

            if continuous:
                if not matches_on_page:
                    consecutive_non_matches += 1  # Count pages with no matches
                    if consecutive_non_matches > 0:
                        break  # Break if a full page without matches is found
            elif found_matches and not continuous:
                break  # Stop after first page with matches if not in continuous mode

    return toc_dict if found_matches else {}



def extract_toc_until_page(pdf_path, end_page, separators=['-', '.', '\s', '*']):
    """Extracts the table of contents up to a certain page number."""
    separator_pattern = "[" + "".join(separators) + "]+"
    regex_pattern = rf'(.+?){separator_pattern}(\d+)$'
    toc_dict = {}

    for page_number in range(end_page):
        text = extract_text_by_page(pdf_path, page_number)
        if text:
            for line in text.split('\n'):
                match = re.search(regex_pattern, line)
                if match:
                    title = match.group(1).strip()
                    page = int(match.group(2))
                    toc_dict[title] = page

    return toc_dict



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
