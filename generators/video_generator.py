import subprocess
from pathlib import Path


def generate_video(voice_path, subtitles_path, output_path):
    voice_path = Path(voice_path)
    subtitles_path = Path(subtitles_path)
    output_path = Path(output_path)
    topic_folder = voice_path.parent

    command = [
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
            "force_style='FontSize=18,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=3,Alignment=2,MarginV=160'"
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

    subprocess.run(command, cwd=topic_folder, check=True)
