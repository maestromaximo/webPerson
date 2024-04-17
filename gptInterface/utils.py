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
   

# Example usage:
# filepath = 'path/to/your/audiofile.mp3'
# transcript_response = transcribe_audio_with_whisper(filepath)
# transcribed_text = transcript_response["text"]
# print(transcribed_text)
