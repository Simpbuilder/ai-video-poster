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
            "source_folder": approval_path.parent,
        })

    return posted_videos


def write_upload_info_file(video, export_path):
    info_path = export_path.with_suffix(".txt")

    if info_path.exists():
        print(f"Upload info already exists: {info_path}")
        return

    topic = video["topic"]
    upload_info = (
        f"Topic: {topic}\n"
        f"Suggested title: {topic}\n"
        f"Suggested caption: Quick explanation: {topic}\n"
        f"Source folder path: {video['source_folder']}\n"
    )

    with open(info_path, "w", encoding="utf-8") as info_file:
        info_file.write(upload_info)

    print(f"Created upload info: {info_path}")


def export_video(video):
    EXPORTS_FOLDER.mkdir(exist_ok=True)

    file_name = make_safe_video_filename(video["topic"])
    export_path = EXPORTS_FOLDER / file_name

    if export_path.exists():
        print(f"Skipped: {video['topic']}")
        print(f"Already exists: {export_path}")
    else:
        shutil.copy(video["video_path"], export_path)

        print(f"Exported: {video['topic']}")
        print(f"Saved to: {export_path}")

    write_upload_info_file(video, export_path)


def main():
    posted_videos = find_posted_videos()

    if not posted_videos:
        print("There are no posted videos ready to export.")
        return

    for video in posted_videos:
        export_video(video)


if __name__ == "__main__":
    main()
