import json
import subprocess
from pathlib import Path


SUBTITLE_STYLE = (
    "FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,Outline=3,Alignment=2,MarginV=160"
)


def srt_time_to_seconds(srt_time):
    hours, minutes, seconds_and_milliseconds = srt_time.split(":")
    seconds, milliseconds = seconds_and_milliseconds.split(",")

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def get_audio_duration(audio_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None

    if duration <= 0:
        return None

    return duration


def find_scene_images(topic_folder):
    scenes_path = topic_folder / "scenes.json"

    if not scenes_path.exists():
        return None

    try:
        with open(scenes_path, "r", encoding="utf-8") as scenes_file:
            scenes = json.load(scenes_file)

        scene_images = []

        for scene in scenes:
            scene_number = scene["scene_number"]
            image_path = topic_folder / f"scene_{scene_number:03}.png"

            if not image_path.exists():
                return None

            scene_images.append({
                "image_path": image_path,
                "start_seconds": srt_time_to_seconds(scene["start_time"]),
                "end_seconds": srt_time_to_seconds(scene["end_time"]),
            })
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    return scene_images or None


def create_dark_background_command(
    voice_path,
    subtitles_path,
    output_path,
):
    return [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=#121212:s=1080x1920:r=30",
        "-i",
        voice_path.name,
        "-vf",
        (
            f"subtitles={subtitles_path.name}:"
            f"force_style='{SUBTITLE_STYLE}'"
        ),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        output_path.name,
    ]


def create_scene_background_command(
    voice_path,
    subtitles_path,
    output_path,
    scene_images,
    audio_duration,
):
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=#121212:s=1080x1920:r=30",
    ]

    for scene in scene_images:
        command.extend([
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            scene["image_path"].name,
        ])

    audio_input_number = len(scene_images) + 1
    command.extend(["-i", voice_path.name])

    filters = []
    previous_background = "[0:v]"

    for position, scene in enumerate(scene_images):
        input_number = position + 1
        scene_label = f"[scene_{input_number}]"
        background_label = f"[background_{input_number}]"

        if position + 1 < len(scene_images):
            display_end = scene_images[position + 1]["start_seconds"]
        else:
            display_end = 99999

        filters.append(
            f"[{input_number}:v]scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1{scene_label}"
        )
        filters.append(
            f"{previous_background}{scene_label}overlay="
            f"enable='between(t,{scene['start_seconds']},"
            f"{display_end})'{background_label}"
        )
        previous_background = background_label

    filters.append(
        f"{previous_background}subtitles={subtitles_path.name}:"
        f"force_style='{SUBTITLE_STYLE}'[video]"
    )

    command.extend([
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[video]",
        "-map",
        f"{audio_input_number}:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        output_path.name,
    ])

    return command


def generate_video(voice_path, subtitles_path, output_path):
    voice_path = Path(voice_path)
    subtitles_path = Path(subtitles_path)
    output_path = Path(output_path)
    topic_folder = voice_path.parent
    scene_images = find_scene_images(topic_folder)

    if scene_images:
        audio_duration = get_audio_duration(voice_path)
        command = create_scene_background_command(
            voice_path,
            subtitles_path,
            output_path,
            scene_images,
            audio_duration,
        )
    else:
        command = create_dark_background_command(
            voice_path,
            subtitles_path,
            output_path,
        )

    subprocess.run(command, cwd=topic_folder, check=True)
