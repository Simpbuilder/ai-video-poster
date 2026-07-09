import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config import IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(api_key=api_key)


def generate_image(prompt, output_path):
    result = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size=IMAGE_SIZE,
        quality=IMAGE_QUALITY,
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    Path(output_path).write_bytes(image_bytes)
