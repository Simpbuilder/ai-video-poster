import json
import subprocess
from pathlib import Path


SUBTITLE_STYLE = (
    "FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,Outline=3,Alignment=2,MarginV=160"
)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FRAME_RATE = 30


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


def find_scene_visuals(topic_folder):
    scenes_path = topic_folder / "scenes.json"

    if not scenes_path.exists():
        return None

    try:
        with open(scenes_path, "r", encoding="utf-8") as scenes_file:
            scenes = json.load(scenes_file)

        scene_visuals = []

        for scene in scenes:
            scene_number = scene["scene_number"]
            video_path = topic_folder / f"scene_{scene_number:03}.mp4"
            image_path = topic_folder / f"scene_{scene_number:03}.png"

            if video_path.exists():
                visual_path = video_path
                visual_type = "video"
            elif image_path.exists():
                visual_path = image_path
                visual_type = "image"
            else:
                return None

            scene_visuals.append({
                "scene_number": scene_number,
                "visual_path": visual_path,
                "visual_type": visual_type,
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

    return scene_visuals or None


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
    scene_visuals,
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

    for scene in scene_visuals:
        if scene["visual_type"] == "video":
            command.extend([
                "-stream_loop",
                "-1",
                "-i",
                scene["visual_path"].name,
            ])
        else:
            command.extend([
                "-loop",
                "1",
                "-framerate",
                str(FRAME_RATE),
                "-i",
                scene["visual_path"].name,
            ])

    audio_input_number = len(scene_visuals) + 1
    command.extend(["-i", voice_path.name])

    filters = []
    previous_background = "[0:v]"

    for position, scene in enumerate(scene_visuals):
        input_number = position + 1
        scene_label = f"[scene_{input_number}]"
        background_label = f"[background_{input_number}]"
        is_final_scene = position + 1 == len(scene_visuals)

        if not is_final_scene:
            display_end = scene_visuals[position + 1]["start_seconds"]
        elif audio_duration is not None:
            display_end = audio_duration
        else:
            display_end = scene["end_seconds"]

        scene_duration = get_scene_duration(scene, display_end)

        filters.append(
            create_scene_visual_filter(
                input_number,
                scene_label,
                scene,
                scene_duration,
            )
        )

        enable_expression = create_overlay_enable_expression(
            scene,
            display_end,
            is_final_scene,
        )

        filters.append(
            f"{previous_background}{scene_label}overlay="
            f"enable='{enable_expression}':eof_action=repeat{background_label}"
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


def get_scene_duration(scene, display_end):
    duration = display_end - scene["start_seconds"]

    if duration > 0:
        return duration

    fallback_duration = scene["end_seconds"] - scene["start_seconds"]

    if fallback_duration > 0:
        return fallback_duration

    return 0.1


def format_seconds(seconds):
    return f"{seconds:.3f}"


def create_scene_visual_filter(input_number, scene_label, scene, scene_duration):
    if scene["visual_type"] == "video":
        return create_video_scene_filter(
            input_number,
            scene_label,
            scene,
            scene_duration,
        )

    return create_static_scene_filter(input_number, scene_label)


def create_static_scene_filter(input_number, scene_label):
    return (
        f"[{input_number}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1{scene_label}"
    )


def create_video_scene_filter(input_number, scene_label, scene, scene_duration):
    start_seconds = format_seconds(scene["start_seconds"])
    duration = format_seconds(scene_duration)

    return (
        f"[{input_number}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,"
        f"fps={FRAME_RATE},trim=duration={duration},"
        f"setpts=PTS-STARTPTS+{start_seconds}/TB{scene_label}"
    )


def create_overlay_enable_expression(scene, display_end, is_final_scene):
    start_seconds = format_seconds(scene["start_seconds"])

    if is_final_scene:
        return f"gte(t,{start_seconds})"

    return f"between(t,{start_seconds},{format_seconds(display_end)})"


def generate_video(voice_path, subtitles_path, output_path):
    voice_path = Path(voice_path)
    subtitles_path = Path(subtitles_path)
    output_path = Path(output_path)
    topic_folder = voice_path.parent
    scene_visuals = find_scene_visuals(topic_folder)

    if scene_visuals:
        audio_duration = get_audio_duration(voice_path)

        print(
            "Image motion is disabled because stable rendering is currently "
            "preferred."
        )
        print("Final scene stays visible until audio ends.")

        if any(scene["visual_type"] == "video" for scene in scene_visuals):
            print("Scene videos detected. Using video clips where available.")

        for scene in scene_visuals:
            print(
                f"Scene {scene['scene_number']} visual: "
                f"{scene['visual_type']}"
            )

        command = create_scene_background_command(
            voice_path,
            subtitles_path,
            output_path,
            scene_visuals,
            audio_duration,
        )
    else:
        command = create_dark_background_command(
            voice_path,
            subtitles_path,
            output_path,
        )

    subprocess.run(command, cwd=topic_folder, check=True)
