import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential
import json
from openai import OpenAI
import tiktoken
import os
from dotenv import load_dotenv
from .models import BudgetCategory, FieldEntry
# Load environment variables from .env file
load_dotenv()

# Fetch the API key from environment variables
# OPENAI_API_KEY = 

# client = OpenAI()

def classify_transaction_simple(entry, set_misc=False):
    description = entry.message.lower()

    # Define keywords for each category
    food_keywords = ['metro', 'freshco', 'shoppers', 'nofrills', 'food basic', 'food', 'eats', 'takeout']
    transport_keywords = ['uber', 'ubertrip','presto', 'taxi']
    insurance_keywords = ['belair']
    entertainment_keywords = ['indigo']

    # Check if any keyword is in the description
    if any(keyword in description for keyword in food_keywords):
        return 'food'
    elif any(keyword in description for keyword in transport_keywords):
        return 'transport'
    elif any(keyword in description for keyword in insurance_keywords):
        return 'insurance'
    elif any(keyword in description for keyword in entertainment_keywords):
        return 'entertainment'
    if set_misc:
        return 'miscellaneous'
    else:
        return None
# gpt-3.5-turbo-0613
# gpt-4-1106-preview
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def classify_transaction_advanced(entry: FieldEntry, model="gpt-4-1106-preview", function_call='classify_entry'):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    categories = """Transportation: This category encompasses all expenses related to transport. It includes fuel costs, public transportation fares, taxi fares, ride-sharing services like Uber, vehicle maintenance, and any other costs associated with getting from one place to another.
Food: This category is for all food-related expenses. It includes solely grocery shopping or food non-takeout related purchases.
Entertainment: This category covers expenses related to personal enjoyment and leisure activities. This can include movie tickets, recreational activities, hobbies, books, and any other expenses incurred for fun and relaxation.
Takeout: Specifically focusing on food ordered from outside (different from general 'Food' which includes groceries), this category includes expenses from food delivery services, fast food, and any other form of prepared food that is purchased to consume.
Supplies: This category encompasses everyday household items and personal care products. It can include toiletries, cleaning supplies, over-the-counter medications, and other miscellaneous items essential for daily living.
Savings payments and transfers: This one is used for transactions that are just E-transfers or payments from an account to another"""
    testing_prompt = f"Here is a purchase entry that was made, it was made in Ontario Canada. Please look at the associated description and categorize it among (transportation, food, entertainment, takeout, supplies), once ready you MUST USE classify_entry with the appropiate category. Here are the general rules \"{categories}\" IF IT IS (e-Transfer sent, to Find & Save,Internet Banking E-TRANSFER 010856074496,). \n Purchase description: \"{entry.message}\"."


    messages = [{"role": "user", "content": testing_prompt}]
    

    json_data = {"model": model, "messages": messages}
    # print(df)
    functions = [{
        "name": "classify_entry",
        "description": "Classify a purchase entry based on a presumed classification category. Returns a boolean indicating whether the presumed classification is accurate.",
        "parameters": {
            "type": "object",
            "properties": {
                "classification": {
                    "type": "string",
                    "description": "The presumed classification of the purchase, which should be one of the following: 'transportation', 'food', 'entertainment', 'takeout', 'supplies'.",
                    "enum": ["transportation", "food", "entertainment", "takeout", "supplies"]
                }
            },
            "required": [
                "classification"
            ]
        },
        "returns": {
            "type": "boolean",
            "description": "The result indicating whether the presumed classification is accurate or not."
        }
    }]
        # available_functions = {}
    if functions is not None and not []: ##if functions empty this gives error
        json_data.update({"functions": functions})
    if function_call is not None and functions != []:
        if function_call == 'auto':
            json_data.update({"function_call": function_call})
        else:
            json_data.update({"function_call": {'name': function_call}})
    # print('FUNCTIONS:', functions)
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        assistant_message = response.json()["choices"][0]["message"]
        # print('ASSISTANT', assistant_message['content'])
      
        if 'function_call' in assistant_message:
            tool_call = assistant_message['function_call']
            function_name = tool_call['name']
            function_args = json.loads(tool_call['arguments'])
            
            # print(function_args)
            try:
                clas = function_args['classification'].lower()
                valid_categories = ['transportation', 'food', 'entertainment', 'takeout', 'supplies']
                if clas not in valid_categories:
                    print(f'it failed, as it categorized as {clas}')
                    return None
                return clas
            except:
                return None
        else:
            return None

    except Exception as e:
        print(f"Error during conversation: {e}")
        return None
    
def update_budget_and_mark_entry(entry: FieldEntry):
   

    if entry.accounted_for == False:
        try:
            budget_category = BudgetCategory.objects.get(name=entry.category)
            budget_category.amount_spent += entry.money
            budget_category.save()

            entry.accounted_for = True
            entry.save()

        except BudgetCategory.DoesNotExist:
            print('missed category!!')
            pass

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def gpt_chat_and_execute_function_bank(question, context, model="gpt-3.5-turbo-0613", function_call='auto'):
    """
    Sends a question to the GPT model and executes a function call based on the response.
    The function call is determined by the model's response or by the most relevant function found in the available functions.

    Parameters:
    - question (str): The user's question or input to be sent to the GPT model.
    - context (list, optional): A list of previous messages for context. Defaults to None.
    - model (str, optional): The GPT model to be used. Defaults to "gpt-3.5-turbo-0613".
    - function_call (str, optional): The type of function call to execute. Defaults to 'auto'.

    Returns:
    - str or None: The response from the GPT model or the output of the executed function, or None in case of an error.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    
    messages = [{"role": "user", "content": question}]
    if context:
        temp = context + messages
        messages = temp
        context = messages

    json_data = {"model": model, "messages": messages}
    # print(df)
    functions = []
    available_functions = {}
    if functions is not None and not []: ##if functions empty this gives error
        json_data.update({"functions": functions})
    if function_call is not None and functions != []:
        json_data.update({"function_call": function_call})
    # print('FUNCTIONS:', functions)
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        assistant_message = response.json()["choices"][0]["message"]
        # print('ASSISTANT', assistant_message['content'])
        if assistant_message['content']:
            # print('not none')
            messages.append({"role": "assistant", "content": assistant_message['content']})
        context = messages

        function_responses = []
        if 'function_call' in assistant_message:
            tool_call = assistant_message['function_call']
            function_name = tool_call['name']
            function_args = json.loads(tool_call['arguments'])
            messages.append({
                "role": "assistant",
                "content": assistant_message.get('content'),
                "function_call": assistant_message['function_call']
            })
            context = messages

            if function_name in available_functions:
                function_response = available_functions[function_name](**function_args)
                function_responses.append({
                    "role": "user",
                    "content": f"This is a hidden system message that just shows you what the function returned, answer the previous user message given that this is what it evaluated to, only pay attention to the values not the prompt I am giving you now: {function_response}"
                })
                messages.extend(function_responses)
                context = messages
            else:
                raise ValueError(f"Function {function_name} not defined.")

            if function_responses:
                
                
                follow_up_response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json={"model": model, "messages": messages})
                follow_up_message = follow_up_response.json()["choices"][0]["message"]
                messages.append({"role": "assistant", "content": follow_up_message['content']})
                context = messages
                return follow_up_message['content'], context
        else:
            return assistant_message['content'], context

    except Exception as e:
        print(f"Error during conversation: {e}")
        return None, messages