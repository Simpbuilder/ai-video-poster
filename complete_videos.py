import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def find_completed_videos():
    completed_videos = []
    approval_folder = Path("approval")

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        video_file = approval.get("video_file")
        video_path = approval_path.parent / video_file if video_file else None

        if (
            approval.get("approved") is True
            and approval.get("status") == "video_generated"
            and video_path is not None
            and video_path.exists()
        ):
            completed_videos.append({
                "path": approval_path,
                "data": approval,
            })

    return completed_videos


def get_completed_folder(source_folder):
    completed_folder = Path("completed")
    completed_folder.mkdir(exist_ok=True)

    destination = completed_folder / source_folder.name
    suffix = 1

    while destination.exists():
        destination = completed_folder / f"{source_folder.name}_{suffix}"
        suffix += 1

    return destination


def main():
    completed_videos = find_completed_videos()

    if not completed_videos:
        print("There are no completed videos ready to move.")
        return

    for completed_video in completed_videos:
        approval_path = completed_video["path"]
        approval = completed_video["data"]
        approval["status"] = "completed"
        approval["completed_at"] = datetime.now(timezone.utc).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        source_folder = approval_path.parent
        destination = get_completed_folder(source_folder)
        shutil.move(str(source_folder), str(destination))

        print(f"Completed: {approval['topic']}")
        print(f"Moved to: {destination}")


if __name__ == "__main__":
    main()
