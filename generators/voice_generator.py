import os

from dotenv import load_dotenv
from openai import OpenAI

from config import VOICE_MODEL, VOICE_NAME

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(api_key=api_key)


def generate_voice(text, output_path):
    with client.audio.speech.with_streaming_response.create(
        model=VOICE_MODEL,
        voice=VOICE_NAME,
        input=text,
    ) as response:
        response.stream_to_file(output_path)
