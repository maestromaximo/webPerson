from openai import OpenAI

# Initialize your OpenAI client with your API key
client = OpenAI()

def transcribe_audio_with_whisper(filepath, language='en'):
    """
    Transcribes the audio file at the given filepath using OpenAI's Whisper model.

    Args:
    filepath (str): The path to the audio file to transcribe.
    language (str): The ISO-639-1 code for the language of the audio (defaults to English).

    Returns:
    dict: The transcription response object.
    """
    print('in transcribe_audio_with_whisper')
    with open(filepath, "rb") as audio_file:
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language
        )
    # print('transcript_response:', transcript_response)
    return transcript_response.text

def generate_chat_completion(user_question, use_gpt4=False):
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