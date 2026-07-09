import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from generators.video_generator import generate_video


def find_items_ready_for_video():
    ready_items = []
    approval_folder = Path("approval")

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        voice_file = approval.get("voice_file")
        subtitles_file = approval.get("subtitles_file")
        voice_path = approval_path.parent / voice_file if voice_file else None
        subtitles_path = (
            approval_path.parent / subtitles_file
            if subtitles_file
            else None
        )

        if (
            approval.get("approved") is True
            and approval.get("status") == "subtitles_generated"
            and voice_path is not None
            and voice_path.exists()
            and subtitles_path is not None
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
        print("There are no subtitle-ready items waiting for video generation.")
        return

    for ready_item in ready_items:
        approval_path = ready_item["path"]
        approval = ready_item["data"]
        video_path = approval_path.parent / "final.mp4"

        if video_path.exists():
            print(f"Video already exists for: {approval['topic']}")
            continue

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
