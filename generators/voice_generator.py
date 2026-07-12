import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config import VOICE_MODEL, VOICE_NAME, VOICE_SPEED

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(api_key=api_key)


def generate_voice(text, output_path):
    output_path = Path(output_path)

    if VOICE_SPEED == 1.0:
        with client.audio.speech.with_streaming_response.create(
            model=VOICE_MODEL,
            voice=VOICE_NAME,
            input=text,
        ) as response:
            response.stream_to_file(output_path)
        return

    raw_voice_path = output_path.with_name("voice.raw.tmp.mp3")
    faster_voice_path = output_path.with_name("voice.faster.tmp.mp3")

    raw_voice_path.unlink(missing_ok=True)
    faster_voice_path.unlink(missing_ok=True)

    with client.audio.speech.with_streaming_response.create(
        model=VOICE_MODEL,
        voice=VOICE_NAME,
        input=text,
    ) as response:
        response.stream_to_file(raw_voice_path)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_voice_path),
                "-filter:a",
                f"atempo={VOICE_SPEED}",
                "-vn",
                str(faster_voice_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        os.replace(faster_voice_path, output_path)
    finally:
        raw_voice_path.unlink(missing_ok=True)
        faster_voice_path.unlink(missing_ok=True)
