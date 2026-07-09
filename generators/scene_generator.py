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
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "narration_text": {"type": "string"},
                        "visual_description": {"type": "string"},
                        "image_prompt": {"type": "string"},
                        "estimated_duration_seconds": {"type": "number"},
                    },
                    "required": [
                        "scene_number",
                        "start_time",
                        "end_time",
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


def generate_scene_plan(scene_groups, original_script):
    prompt = (
        "Create a visual plan for these timed YouTube Shorts scenes. "
        "Return one scene for every scene group. Keep each scene number, "
        "timestamp, and duration exactly as provided. Clean up each scene's "
        "narration text using the original script to correct transcription "
        "mistakes where possible. Keep the narration aligned with its timed "
        "subtitle group. "
        "Add a clear visual description and a detailed image-generation "
        "prompt for each scene."
    )
    scene_request = {
        "timed_subtitle_groups": scene_groups,
        "original_script": original_script,
    }

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(scene_request, indent=2),
                },
            ],
            text={"format": SCENE_PLAN_SCHEMA},
        )
        scene_plan = json.loads(response.output_text)
        generated_scenes = scene_plan["scenes"]

        visuals_by_number = {
            scene["scene_number"]: scene
            for scene in generated_scenes
        }

        final_scenes = []

        for scene_group in scene_groups:
            scene_number = scene_group["scene_number"]
            visual_plan = visuals_by_number[scene_number]

            final_scenes.append({
                **scene_group,
                "narration_text": visual_plan["narration_text"],
                "visual_description": visual_plan["visual_description"],
                "image_prompt": visual_plan["image_prompt"],
            })
    except Exception as error:
        raise SceneGenerationError(str(error)) from error

    return final_scenes
