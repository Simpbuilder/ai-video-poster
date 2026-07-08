import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(api_key=api_key)

MODEL_NAME = "gpt-5.4-mini"


class ScriptGenerationError(Exception):
    pass


def generate_script(topic):
    prompt_template = Path("prompts/script_writer.txt").read_text(
        encoding="utf-8"
    ).rstrip("\r\n")
    prompt = prompt_template.replace("{topic}", topic)

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=prompt,
        )
    except Exception as error:
        raise ScriptGenerationError(str(error)) from error

    return response.output_text
