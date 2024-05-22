import PyPDF2
import os
from dotenv import load_dotenv
import openai
import json
import subprocess
import fitz  # PyMuPDF
import re
from pinecone import Pinecone
from tqdm import tqdm
import itertools
import numpy as np
import concurrent.futures
from functools import partial
import tempfile
import shutil
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadedfile import UploadedFile
from io import BytesIO
from pydub import AudioSegment
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
from PyPDF2 import PdfReader, PdfWriter

MODELS = {
    'gpt-4': 'gpt-4o',
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

## Pinecone API
pc_api_key = os.getenv("PINECONE_API_KEY")
pc_index_name = "websiteindex"
pc = Pinecone(api_key=pc_api_key)
pc_index = pc.Index(pc_index_name)
## Pinecone API


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


## embending

##A key note for this fucntion is that we will be feeding it both mathematical text as well as the text from the pdf file, not sure if fourmulas will carry meaning in the text-embedding-3-large model
def generate_embedding(text, model="text-embedding-3-large"):
    """
    Generate an embedding for the given text using the specified model.
    :param text: The input text to embed.
    :param model: The name of the model to use for embedding.
    :return: The embedding vector for the input text.
    """
    response = client.embeddings.create(
        input=text,
        model=model
    )

    return response.data[0].embedding

## embending

def chunk_text_advanced(text, min_words=310, max_words=1200, use_separators=True, context_window=100):
    """Chunk the text intelligently with options for using separators and adding context windows."""
    chunks = []
    if use_separators:
        # Split by newlines to get paragraphs
        paragraphs = text.split('\n')
    else:
        # Treat the entire text as one single block and split by whitespace
        paragraphs = [' '.join(text.split())]

    current_chunk = []
    current_word_count = 0
    paragraph_count = len(paragraphs)

    for paragraph in tqdm(paragraphs, desc=f"Processing/chunking/paragraphs, separators={use_separators},len={paragraph_count}"):
        words = paragraph.split()
        for word in words:
            current_chunk.append(word)
            current_word_count += 1

            if current_word_count >= min_words:
                if current_word_count + len(words) > max_words:
                    # Slice the current chunk to not exceed the maximum word count
                    excess_words = (current_word_count + len(words)) - max_words
                    final_chunk = current_chunk[:-excess_words]
                else:
                    final_chunk = current_chunk[:]

                # Converting list back to string and managing context window
                chunk_str = ' '.join(add_context_window(final_chunk, words, context_window))
                chunks.append(chunk_str)
                # Reset the chunk
                current_chunk = []
                current_word_count = 0

    # Handle the last chunk if it meets the minimum words criteria
    if current_word_count >= min_words:
        chunk_str = ' '.join(add_context_window(current_chunk, words, context_window))
        chunks.append(chunk_str)

    return chunks

def add_context_window(chunk, remaining_words, context_window):
    """Add context window words to the beginning and end of the chunk."""
    start_context = max(0, len(chunk) - context_window)
    end_context = min(len(remaining_words), context_window)
    return chunk[start_context:] + remaining_words[:end_context]


def embed_book_text(pdf_path, min_words=310, max_words=1200, use_separators=True, context_window=100, model="text-embedding-3-large"):
    """Embed the text from a PDF book, chunk the text, and generate embeddings for each chunk with associated text."""
    text = extract_text_from_pdf(pdf_path)  # Extract text from the PDF
    chunks = chunk_text_advanced(text, min_words=min_words, max_words=max_words, use_separators=use_separators, context_window=context_window)
    
    vectors = []
    for i, chunk in enumerate(tqdm(chunks, desc="Generating embeddings")):
        embedding = generate_embedding(chunk, model=model)
        # Append the embedding with an ID and include the chunk text as metadata
        vectors.append({"id": str(i + 1), "vector": embedding, "text": chunk})

    return vectors





## Pinecone integration


def chunks(iterable, batch_size=100):
    """A helper function to break an iterable into chunks of size batch_size."""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))

def upload_book_to_index(pdf_path, book_name_slug):
    """Upload the text from a PDF book to the Pinecone index asynchronously."""
    vector_embeddings = embed_book_text(pdf_path)  # Assuming this returns a list of {"id": "1", "values": [0.1, ...]}

    # Chunk embeddings and upsert them in parallel
    pc_parallel = Pinecone(api_key=pc_api_key, pool_threads=30)
    index_parallel = pc_parallel.Index(pc_index_name)
    
    for embeddings_chunk in chunks(vector_embeddings, batch_size=100):
        # Prepare upsert data including metadata
        upsert_data = [(item['id'], item['vector'], {"text": item['text']}) for item in embeddings_chunk]
        index_parallel.upsert(vectors=upsert_data, async_req=True, namespace=book_name_slug.lower())

    print("Book embeddings with metadata uploaded to Pinecone index.")

def get_all_namespaces():
    """Get all the namespaces in the Pinecone index.
    Returns a list of stings representing the namespaces."""
    index_stats = pc_index.describe_index_stats()
    namespaces_dict = index_stats['namespaces']
    return list(namespaces_dict.keys())

@DeprecationWarning
def query_pineconeOLD(query, embed=True, top_k=5, return_top=True, model="text-embedding-3-large", namespace=None):
    """
    Query Pinecone index with either a text string or a vector, specifying an optional namespace.
    :param query: Text to embed or a vector.
    :param embed: Boolean indicating whether the query is a text that needs embedding.
    :param top_k: Number of top results to return.
    :param return_top: If True, return only the top result with the highest score; otherwise, return all top_k results.
    :param model: The model to use for text embedding.
    :param namespace: The namespace within the Pinecone index to query. This is where we provide the Book slug as namespace to search by book.
    """
    if embed:
        # Generate an embedding if the input is text
        query_vector = generate_embedding(query, model=model)
    else:
        # Assume the input is already a vector
        query_vector = query

    # Prepare query options
    query_options = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True
    }
    if namespace:
        query_options["namespace"] = namespace
    else:
        namespaces = get_all_namespaces()
        ##in parallel query all namespaces
        
    

    # Query Pinecone with metadata inclusion and optional namespace
    
    results = pc_index.query(**query_options)
    # print('DEBUG: results:', results)

    # Extract the IDs, scores, and text from the top results
    matches = results['matches']
    formatted_results = [{"text": match["metadata"]["text"], "score": float(match["score"])} for match in matches]

    # Sort results by score in descending order
    sorted_results = sorted(formatted_results, key=lambda x: x['score'], reverse=True)

    if return_top:
        # Return only the top result with the highest score
        top_result = sorted_results[0].get('text', 'none') if sorted_results else None
        return top_result
    else:
        # Return all top_k results
        return sorted_results
    
def query_pinecone(query, embed=True, top_k=5, return_top=True, model="text-embedding-3-large", namespace=None):
    """
    Query Pinecone index with either a text string or a vector, specifying an optional namespace.
    If no namespace is provided, queries all namespaces in parallel and returns the top result across all.
    """
    if embed:
        # Generate an embedding if the input is text
        query_vector = generate_embedding(query, model=model)
    else:
        # Assume the input is already a vector
        query_vector = query

    if namespace:
        return single_namespace_query(query_vector, top_k, namespace) if not return_top else single_namespace_query(query_vector, top_k, namespace)[0]['text']
    else:
        return query_all_namespaces(query_vector, top_k)

def single_namespace_query(query_vector, top_k, namespace):
    """Query a single namespace and return the results."""
    query_options = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True,
        "namespace": namespace
    }
    results = pc_index.query(**query_options)
    matches = results['matches']
    return [{"text": match["metadata"]["text"], "score": float(match["score"])} for match in matches]

def query_all_namespaces(query_vector, top_k):
    """Query all namespaces in parallel and return the top result."""
    namespaces = get_all_namespaces()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Prepare partial function to query each namespace
        func = partial(single_namespace_query, query_vector, top_k)
        # Map function across all namespaces
        futures = {executor.submit(func, namespace=ns): ns for ns in namespaces}
        all_results = []

        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

    # Aggregate and sort results from all namespaces
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[0]['text'] if all_results else None



def cosine_similarity(vec1, vec2):
    """Calculate the cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0  # Avoid division by zero
    similarity = dot_product / (norm_vec1 * norm_vec2)
    return similarity
## Pinecone integration



def generate_chat_completionOLD(user_question, use_gpt4=False):
    """
    Generates a chat completion using OpenAI's GPT-3.5-turbo or GPT-4 model.

    Args:
    user_question (str): The user's question.
    use_gpt4 (bool): Whether to use GPT-4 model or not (defaults to False).

    Returns:
    str: The generated completion message.
    """
    model = "gpt-4o" if use_gpt4 else "gpt-3.5-turbo"
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_question}
        ]
    )
    return completion.choices[0].message.content

def generate_chat_completion(user_question, use_gpt4=True):
    """
    Generates a chat completion using OpenAI's GPT-3.5-turbo or GPT-4 model.
    If the context length exceeds the maximum for GPT-3.5-turbo, it retries with GPT-4.

    Args:
    user_question (str): The user's question.
    use_gpt4 (bool): Whether to use GPT-4 model or not (defaults to False).

    Returns:
    str: The generated completion message.
    """
    model = "gpt-4o" if use_gpt4 else "gpt-3.5-turbo"
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_question}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        if 'context_length_exceeded' in str(e):
            if not use_gpt4:  # Only retry with GPT-4 if it wasn't already using it
                return generate_chat_completion(user_question, use_gpt4=True)
            else:
                # Handle case where GPT-4 also exceeds context length or throw the error if needed
                raise ValueError("Error: The provided context is too long, even for GPT-4.")
        else:
            raise e
        
def extract_the_most_likely_title(lesson_summary, book_index, use_gpt4=False):
    """
    Generates a likely book index section based on the lesson summary using OpenAI's GPT model.

    Args:
    lesson_summary (str): The lesson summary text.
    book_index (str): The book index text.
    use_gpt4 (bool): Whether to use GPT-4 model or not (defaults to False).

    Returns:
    str: The generated book index section.
    """
    model = "gpt-4o" if use_gpt4 else "gpt-3.5-turbo"
    completion = client.chat.completions.create(
        model=model,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are a helpful assistant dessigned to always output JSON."},
            {"role": "user", "content": f"Please output the most likely book index title and page number for the following lesson summary:\n{lesson_summary}\nGiven the book index:\n{book_index}\nSample output:"+ "{'title': 'Chapter 1: Introduction', 'page': '1'}"},
        ]
    )
    response = completion.choices[0].message.content
    try:
        json_response = json.loads(response)
        ##return the title and page number and we return independent of the keys they two values from the expected dictionary output, but we return none if there are not exactly two values
        values = list(json_response.values())
        return values[0], values[1] if len(values) == 2 else None
    except Exception as e:
        print(f"Error parsing JSON response: {str(e)}")
        return None

def get_gpt_response_with_context(session, user_question:str, use_gpt4=True, lesson_slug=None, class_slug=None):
    """
    Generates a chat completion using OpenAI's GPT model, including context from previous messages.

    Args:
        session (ChatSession): The chat session object containing messages.
        user_question (str): The user's current question.
        use_gpt4 (bool): Whether to use GPT-4 model (defaults to False, using GPT-3.5-turbo instead).

    Returns:
        str: The generated completion message.
    """
    # Select the appropriate model based on the function argument
    from .models import Message
    model_version = "gpt-4o" if use_gpt4 else "gpt-3.5-turbo"

    # Build the conversation history for context
    messages = session.messages.all()
    conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]
    for message in messages:
        role = "user" if message.role == 'user' else "assistant"
        conversation_history.append({"role": role, "content": message.text})

    # Add the current user question to the conversation history
    conversation_history.append({"role": "user", "content": user_question})
    
    # print(f'conversation_history: {conversation_history}')
    # Generate the completion with OpenAI API
    response = client.chat.completions.create(
        model=model_version,
        messages=conversation_history
    )

    ##create and append the messages to session
    # new_message = Message(session=session, role='user', text=user_question)
    # new_message.save()
    # assistant_response = Message(session=session, role='assistant', text=response.choices[0].message.content)
    # assistant_response.save()
    
    return response.choices[0].message.content


@DeprecationWarning
def transcribe_audioOLD(audio_file, model="whisper-1"):
    """
    DEPRECATION: The reason behind the deprecation is because when published to a server, like pythonanywhere, the client yields an error this way openai.BadRequestError: Error code: 400 - {'error': {'message': "Unrecognized file format. Supported formats: ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']", 'type': 'invalid_request_error', 'param': None, 'code': None}}. Functional locally

    Transcribe the audio file using the specified model.

    Args:
    audio_file: The audio file.
    model (str): The model to use for transcription (defaults to "whisper-1").

    Returns:
    str: The transcribed text from the audio file.
    """
     # OpenAI expects a file path or file-like object; we will use a NamedTemporaryFile to handle this.
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
        # Write the uploaded file's contents to the temporary file
        for chunk in audio_file.chunks():
            tmp.write(chunk)
        tmp.seek(0)  # Rewind the file pointer to the beginning of the file
        
        # Use the OpenAI API to transcribe the audio
        response = client.audio.transcriptions.create(
            file=tmp.file,  # Pass the temporary file object
            model=model
        )
        
        # Ensure to close and delete the temporary file
        tmp.close()
    # print('response:', response)
    return response.text

def transcribe_audio_local(audio_file_path, model="whisper-1"):
    """
    Transcribe the audio file using the specified model, handling large files by segmenting them into smaller chunks. LOCAL

    Args:
        audio_file_path (str): The path to the audio file.
        model (str): The model to use for transcription (defaults to "whisper-1").

    Returns:
        str: The concatenated transcribed text from all segments of the audio file.
    """
    # Calculate file size in megabytes
    file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
    ten_minutes = 10 * 60 * 1000  # Duration of each audio segment in milliseconds
    
    # Read the audio file content
    audio_content = AudioSegment.from_file(audio_file_path)

    # Check if the file needs to be segmented
    if file_size_mb > 23:
        parts = [audio_content[i:i + ten_minutes] for i in range(0, len(audio_content), ten_minutes)]
    else:
        parts = [audio_content]

    # Transcribe each part and concatenate the results
    transcription_results = []
    for part in parts:
        buffer = BytesIO()
        part.export(buffer, format="mp3")  # Export to buffer as mp3
        buffer.seek(0)  # Rewind buffer to the start
        buffer.name = os.path.basename(audio_file_path)  # Set the file name for the buffer
        
        try:
            response = client.audio.transcriptions.create(
                file=buffer,
                model=model
            )
            transcription_results.append(response.text)
        except Exception as e:
            # Handle transcription errors, possibly log them, and continue with next part
            print(f"Error transcribing part: {str(e)}")
    
    # Concatenate all transcription texts
    return " ".join(transcription_results)

def transcribe_audio(audio_file, model="whisper-1"):
    """
    Transcribe the audio file using the specified model, handling large files by segmenting them into smaller chunks.

    Args:
        audio_file: The Django UploadedFile object from the form.
        model (str): The model to use for transcription (defaults to "whisper-1").

    Returns:
        str: The concatenated transcribed text from all segments of the audio file.
    """
    if isinstance(audio_file, UploadedFile):
        # Calculate file size in megabytes
        file_size_mb = audio_file.size / (1024 * 1024)
        ten_minutes = 10 * 60 * 1000  # Duration of each audio segment in milliseconds
        
        # Read the audio file content
        audio_content = AudioSegment.from_file_using_temporary_files(audio_file)

        # Check if the file needs to be segmented
        if file_size_mb > 23:
            parts = [audio_content[i:i + ten_minutes] for i in range(0, len(audio_content), ten_minutes)]
        else:
            parts = [audio_content]

        # Transcribe each part and concatenate the results
        transcription_results = []
        for part in parts:
            buffer = BytesIO()
            part.export(buffer, format="mp3")  # Export to buffer as mp3
            buffer.seek(0)  # Rewind buffer to the start
            buffer.name = audio_file.name  # Set the file name for the buffer
            
            try:
                response = client.audio.transcriptions.create(
                    file=buffer,
                    model=model
                )
                transcription_results.append(response.text)
            except Exception as e:
                # Handle transcription errors, possibly log them, and continue with next part
                print(f"Error transcribing part: {str(e)}")
        
        # Concatenate all transcription texts
        return " ".join(transcription_results)

    else:
        raise ValueError("The file must be an uploaded file object.")

###### Assigment breaker

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def extract_pages_as_images(pdf_path):
    return convert_from_path(pdf_path)

def detect_question_number(image, i, debug=False):
    left = image.width - 120
    top = 0
    right = image.width
    bottom = 120

    cropped = image.crop((left, top, right, bottom))
    if debug:
        draw = ImageDraw.Draw(image)
        draw.rectangle(((left, top), (right, bottom)), outline="red")
        image.save(f'debug_{i}.png')
        cropped.save(f'debug_cropped_{i}.png')
        
    recognized_text = pytesseract.image_to_string(cropped, config='--psm 6 --oem 1').strip()
    print(f"OCR recognized text on page {i}: {recognized_text}")

    match = re.search(r'[1-9]|i|x|X', recognized_text)
    if match:
        recognized_digit = match.group()
        if recognized_digit.lower() == 'x':
            print(f"OCR detected 'x' or 'X' on page {i}, discarding this page.")
            return False
        elif recognized_digit == 'i':
            print(f"OCR recognized 'i' as '1' on page {i}.")
            return 1
        else:
            return int(recognized_digit)
    else:
        print(f"OCR didn't find a number between 1 and 9, 'i', 'x' or 'X' on page {i}.")
        return None

def create_pdf_from_pages(pdf_reader, pages, output_path):
    pdf_writer = PdfWriter()
    for page_num in pages:
        page = pdf_reader.getPage(page_num)
        pdf_writer.addPage(page)
    with open(output_path, "wb") as output_pdf:
        pdf_writer.write(output_pdf)