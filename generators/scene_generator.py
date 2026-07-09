import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from config import OPENAI_MODEL


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(api_key=api_key)


SCENE_PLAN_SCHEMA = {
    "type": "json_schema",
    "name": "scene_plan",
    "schema": {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "narration_text": {"type": "string"},
                        "visual_description": {"type": "string"},
                        "image_prompt": {"type": "string"},
                        "estimated_duration_seconds": {"type": "number"},
                    },
                    "required": [
                        "scene_number",
                        "narration_text",
                        "visual_description",
                        "image_prompt",
                        "estimated_duration_seconds",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["scenes"],
        "additionalProperties": False,
    },
    "strict": True,
}


class SceneGenerationError(Exception):
    pass


def generate_scene_plan(script):
    prompt = (
        "Create a scene plan for this YouTube Shorts script. "
        "Split the narration into short, logical scenes. "
        "Keep the narration text in its original order. "
        "Describe one clear visual for each scene and write a detailed "
        "image-generation prompt. Estimate how many seconds each scene lasts."
    )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": script},
            ],
            text={"format": SCENE_PLAN_SCHEMA},
        )
        scene_plan = json.loads(response.output_text)
    except Exception as error:
        raise SceneGenerationError(str(error)) from error

    return scene_plan["scenes"]
