import json
import shutil
from pathlib import Path


POSTED_FOLDER = Path("posted")
EXPORTS_FOLDER = Path("exports")
UNSAFE_FILENAME_CHARACTERS = '<>:"/\\|?*'


def make_safe_video_filename(topic):
    safe_name = topic.lower()
    safe_name = safe_name.replace(" ", "-")
    safe_name = safe_name.replace("'", "")
    safe_name = safe_name.replace("\u2019", "")

    for character in UNSAFE_FILENAME_CHARACTERS:
        safe_name = safe_name.replace(character, "")

    return f"{safe_name}.mp4"


def find_posted_videos():
    posted_videos = []

    if not POSTED_FOLDER.exists():
        return posted_videos

    for approval_path in POSTED_FOLDER.rglob("approval.json"):
        video_path = approval_path.parent / "final.mp4"

        if not video_path.exists():
            continue

        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        posted_videos.append({
            "topic": approval.get("topic", "untitled video"),
            "video_path": video_path,
        })

    return posted_videos


def export_video(video):
    EXPORTS_FOLDER.mkdir(exist_ok=True)

    file_name = make_safe_video_filename(video["topic"])
    export_path = EXPORTS_FOLDER / file_name

    if export_path.exists():
        print(f"Skipped: {video['topic']}")
        print(f"Already exists: {export_path}")
        return

    shutil.copy(video["video_path"], export_path)

    print(f"Exported: {video['topic']}")
    print(f"Saved to: {export_path}")


def main():
    posted_videos = find_posted_videos()

    if not posted_videos:
        print("There are no posted videos ready to export.")
        return

    for video in posted_videos:
        export_video(video)


if __name__ == "__main__":
    main()
