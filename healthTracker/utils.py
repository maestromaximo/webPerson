import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential
import json
from openai import OpenAI
import tiktoken, random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def gpt_chat(question, model="gpt-3.5-turbo-0613"):
    """
    Sends a question to the GPT model
    """
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    
    messages = [{"role": "user", "content": question}]
    
    json_data = {"model": model, "messages": messages}
    # print(df)
   
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        assistant_message = response.json()["choices"][0]["message"]
        # print('ASSISTANT', assistant_message['content'])
        
        

        return assistant_message['content']

    except Exception as e:
        print(f"Error during conversation: {e}")
        return None, messages



@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def meal_recipe_creator(food_items, model="gpt-3.5-turbo-0613"):
    """
    Sends a question to the GPT model
    """
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    prompt = f"Please provide a healthy and great recipes and meals given the following items avalible to you. YOU MUST INCLUDE FULL INSTRUCTIONS, and if followed the user would be able to recreate the meal, this is food for lunch. Here are the items: \n {food_items}"
    messages = [{"system": "You are a recipe creator machine, you will always create accurate, tasty, and easy to follow, recepies given the avalible items."},
                {"role": "user", "content": prompt}]
    

    json_data = {"model": model, "messages": messages}
    # print(df)
   
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        assistant_message = response.json()["choices"][0]["message"]
        receipe = assistant_message['content']
        # print('ASSISTANT', assistant_message['content'])
        if assistant_message['content']:
            # print('not none')
            messages.append({"role": "assistant", "content": assistant_message['content']})
       
        random_number = random.randint(1000, 9999)

        # Concatenate 'meal#' with the random number
        meal_name = 'No name'

        gpt_name = gpt_chat(question=f'Please ONLY PROVIDE A SINGLE LINE. YOU MUST ELSE YOU FAIL. What is an appropiate name for this meal RETURN ONLY A STRING WITH THE NAME, NO CHITCHATTER OR ANYTHING ELSE WE FAIL: \"{receipe}\"')

        if gpt_name:
            meal_name = gpt_name
        else:
            meal_name = 'meal#' + str(random_number)

        return receipe, meal_name

    except Exception as e:
        print(f"Error during conversation: {e}")
        return None
    
