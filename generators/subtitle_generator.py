import os
import subprocess
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

TRANSCRIPTION_MODEL = "whisper-1"


def split_items_into_chunks(items):
    chunks = []
    position = 0

    while position < len(items):
        remaining_items = len(items) - position

        if remaining_items <= 5:
            chunk_size = remaining_items
        else:
            chunk_size = 4

            if remaining_items - chunk_size < 3:
                chunk_size = remaining_items - 3

        chunks.append(items[position:position + chunk_size])
        position += chunk_size

    return chunks


def split_into_chunks(script):
    word_chunks = split_items_into_chunks(script.split())
    return [" ".join(words) for words in word_chunks]


def get_word_timestamps(voice_path):
    with open(voice_path, "rb") as voice_file:
        transcription = client.audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL,
            file=voice_file,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )

    words = getattr(transcription, "words", None)

    if not words:
        return []

    return [
        {
            "word": word.word.strip(),
            "start": word.start,
            "end": word.end,
        }
        for word in words
        if word.word.strip()
    ]


def get_audio_duration(voice_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(voice_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def format_srt_time(total_seconds):
    total_milliseconds = round(total_seconds * 1000)
    hours = total_milliseconds // 3_600_000
    minutes = (total_milliseconds % 3_600_000) // 60_000
    seconds = (total_milliseconds % 60_000) // 1000
    milliseconds = total_milliseconds % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def create_word_timed_subtitles(word_timestamps):
    subtitles = []
    word_chunks = split_items_into_chunks(word_timestamps)

    for word_chunk in word_chunks:
        subtitles.append({
            "text": " ".join(word["word"] for word in word_chunk),
            "start": word_chunk[0]["start"],
            "end": word_chunk[-1]["end"],
        })

    return subtitles


def create_duration_based_subtitles(script, voice_path):
    chunks = split_into_chunks(script)

    if not chunks:
        return []

    audio_duration = get_audio_duration(voice_path)
    seconds_per_chunk = audio_duration / len(chunks)
    subtitles = []

    for number, chunk in enumerate(chunks, start=1):
        subtitles.append({
            "text": chunk,
            "start": (number - 1) * seconds_per_chunk,
            "end": number * seconds_per_chunk,
        })

    return subtitles


def write_subtitles(subtitles, output_path):
    subtitle_lines = []

    for number, subtitle in enumerate(subtitles, start=1):
        subtitle_lines.append(str(number))
        subtitle_lines.append(
            f"{format_srt_time(subtitle['start'])} --> "
            f"{format_srt_time(subtitle['end'])}"
        )
        subtitle_lines.append(subtitle["text"])
        subtitle_lines.append("")

    Path(output_path).write_text(
        "\n".join(subtitle_lines),
        encoding="utf-8",
    )


def generate_subtitles(script, voice_path, output_path):
    try:
        word_timestamps = get_word_timestamps(voice_path)
    except Exception:
        word_timestamps = []

    if word_timestamps:
        subtitles = create_word_timed_subtitles(word_timestamps)
    else:
        print("Word timestamps unavailable. Using duration-based timing.")
        subtitles = create_duration_based_subtitles(script, voice_path)

    write_subtitles(subtitles, output_path)
