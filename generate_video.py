import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from config import FORCE_REGENERATE_VIDEO
from generators.video_generator import generate_video


def find_items_ready_for_video():
    ready_items = []
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
            voice_path = topic_folder / "voice.mp3"
            subtitles_path = topic_folder / "subtitles.srt"

            if (
                approval.get("approved") is True
                and approval.get("status") in allowed_statuses
                and voice_path.exists()
                and subtitles_path.exists()
            ):
                ready_items.append({
                    "path": approval_path,
                    "data": approval,
                    "voice_path": voice_path,
                    "subtitles_path": subtitles_path,
                })

    return ready_items


def main():
    ready_items = find_items_ready_for_video()

    if not ready_items:
        print("There are no items ready for video generation.")
        return

    for ready_item in ready_items:
        approval_path = ready_item["path"]
        approval = ready_item["data"]
        video_path = approval_path.parent / "final.mp4"

        if video_path.exists() and not FORCE_REGENERATE_VIDEO:
            print(f"Video already exists for: {approval['topic']}")
            continue

        if video_path.exists():
            print(f"Regenerating video for: {approval['topic']}")

        print(f"Generating video for: {approval['topic']}")

        try:
            generate_video(
                ready_item["voice_path"],
                ready_item["subtitles_path"],
                video_path,
            )
        except FileNotFoundError:
            print("ffmpeg was not found. Install ffmpeg and add it to PATH.")
            return
        except subprocess.CalledProcessError:
            print(f"Could not generate video for: {approval['topic']}")
            continue

        if approval["status"] == "subtitles_generated":
            approval["status"] = "video_generated"

        approval["video_file"] = "final.mp4"
        approval["video_generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        print(f"Saved video: {video_path}")


if __name__ == "__main__":
    main()
