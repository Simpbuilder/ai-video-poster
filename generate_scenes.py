import json
import re
from datetime import datetime, timezone
from pathlib import Path

from config import FORCE_REGENERATE_SCENES
from generators.scene_generator import (
    SceneGenerationError,
    generate_scene_plan,
)


# Higher numbers create fewer longer scenes; lower numbers create more shorter scenes.
SUBTITLES_PER_SCENE = 5


def srt_time_to_seconds(srt_time):
    hours, minutes, seconds_and_milliseconds = srt_time.split(":")
    seconds, milliseconds = seconds_and_milliseconds.split(",")

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def read_subtitles(subtitles_path):
    content = subtitles_path.read_text(encoding="utf-8").strip()

    if not content:
        return []

    subtitle_blocks = re.split(r"\r?\n\r?\n", content)
    subtitles = []

    for block in subtitle_blocks:
        lines = block.splitlines()
        start_time, end_time = lines[1].split(" --> ")
        narration_text = " ".join(lines[2:])

        subtitles.append({
            "start_time": start_time,
            "end_time": end_time,
            "narration_text": narration_text,
        })

    return subtitles


def create_scene_groups(subtitles):
    scene_groups = []

    for position in range(0, len(subtitles), SUBTITLES_PER_SCENE):
        subtitle_group = subtitles[position:position + SUBTITLES_PER_SCENE]
        start_time = subtitle_group[0]["start_time"]
        end_time = subtitle_group[-1]["end_time"]
        duration = (
            srt_time_to_seconds(end_time)
            - srt_time_to_seconds(start_time)
        )

        scene_groups.append({
            "scene_number": len(scene_groups) + 1,
            "start_time": start_time,
            "end_time": end_time,
            "narration_text": " ".join(
                subtitle["narration_text"]
                for subtitle in subtitle_group
            ),
            "estimated_duration_seconds": round(duration, 3),
        })

    return scene_groups


def find_scripts_ready_for_scenes():
    ready_scripts = []
    allowed_statuses = [
        "subtitles_generated",
        "video_generated",
        "completed",
    ]

    for folder_name in ["approval", "completed"]:
        folder = Path(folder_name)

        for approval_path in folder.rglob("approval.json"):
            with open(approval_path, "r", encoding="utf-8") as approval_file:
                approval = json.load(approval_file)

            topic_folder = approval_path.parent
            script_path = topic_folder / "script.txt"
            subtitles_path = topic_folder / "subtitles.srt"

            if (
                approval.get("approved") is True
                and approval.get("status") in allowed_statuses
                and script_path.exists()
                and subtitles_path.exists()
            ):
                ready_scripts.append({
                    "path": approval_path,
                    "data": approval,
                    "script_path": script_path,
                    "subtitles_path": subtitles_path,
                })

    return ready_scripts


def main():
    ready_scripts = find_scripts_ready_for_scenes()

    if not ready_scripts:
        print("There are no scripts ready for scene planning.")
        return

    for ready_script in ready_scripts:
        approval_path = ready_script["path"]
        approval = ready_script["data"]
        topic_folder = approval_path.parent
        scenes_path = topic_folder / "scenes.json"

        if scenes_path.exists() and not FORCE_REGENERATE_SCENES:
            print(f"Scene plan already exists for: {approval['topic']}")
            continue

        if scenes_path.exists():
            print(f"Regenerating scene plan for: {approval['topic']}")

        try:
            original_script = ready_script["script_path"].read_text(
                encoding="utf-8"
            )
            subtitles = read_subtitles(ready_script["subtitles_path"])
            scene_groups = create_scene_groups(subtitles)

            if not scene_groups:
                print(f"Subtitles are empty for: {approval['topic']}")
                continue

            scenes = generate_scene_plan(scene_groups, original_script)
        except FileNotFoundError:
            print(f"Script file is missing for: {approval['topic']}")
            continue
        except (IndexError, ValueError):
            print(f"Could not read subtitles for: {approval['topic']}")
            continue
        except SceneGenerationError as error:
            print(
                f"Could not generate scenes for "
                f"'{approval['topic']}': {error}"
            )
            continue

        with open(scenes_path, "w", encoding="utf-8") as scenes_file:
            json.dump(scenes, scenes_file, indent=4)

        approval["scenes_file"] = "scenes.json"
        approval["scenes_generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        print(f"Saved scene plan: {scenes_path}")


if __name__ == "__main__":
    main()
