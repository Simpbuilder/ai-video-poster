import json
import shutil
from pathlib import Path


def find_completed_videos():
    completed_videos = []
    completed_folder = Path("completed")

    for approval_path in completed_folder.rglob("approval.json"):
        video_path = approval_path.parent / "final.mp4"

        if not video_path.exists():
            continue

        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        completed_videos.append({
            "approval_path": approval_path,
            "video_path": video_path,
            "data": approval,
        })

    return completed_videos


def get_available_destination(source_folder, destination_name):
    destination_folder = Path(destination_name)
    destination_folder.mkdir(exist_ok=True)

    destination = destination_folder / source_folder.name
    suffix = 1

    while destination.exists():
        destination = destination_folder / f"{source_folder.name}_{suffix}"
        suffix += 1

    return destination


def move_reviewed_video(video, status, destination_name):
    approval = video["data"]
    approval["status"] = status

    with open(
        video["approval_path"],
        "w",
        encoding="utf-8",
    ) as approval_file:
        json.dump(approval, approval_file, indent=4)

    source_folder = video["approval_path"].parent
    destination = get_available_destination(
        source_folder,
        destination_name,
    )
    shutil.move(str(source_folder), str(destination))

    print(f"Moved: {approval['topic']}")
    print(f"Destination: {destination}")


def approve_video(video):
    move_reviewed_video(video, "approved_final", "posted")


def reject_video(video):
    move_reviewed_video(video, "rejected_final", "rejected")


def main():
    completed_videos = find_completed_videos()

    if not completed_videos:
        print("There are no completed videos waiting for final review.")
        return

    print("Completed videos:")

    for number, video in enumerate(completed_videos, start=1):
        print(f"{number}. {video['data']['topic']}")
        print(f"   Video: {video['video_path']}")

    print("\nType approve, reject, skip, all, or q to quit.")

    position = 0

    while position < len(completed_videos):
        video = completed_videos[position]
        topic = video["data"]["topic"]
        choice = input(f"\nReview '{topic}': ").strip().lower()

        if choice == "approve":
            approve_video(video)
            position += 1
        elif choice == "reject":
            reject_video(video)
            position += 1
        elif choice == "skip":
            print(f"Skipped: {topic}")
            position += 1
        elif choice == "all":
            for remaining_video in completed_videos[position:]:
                approve_video(remaining_video)
            return
        elif choice == "q":
            print("Final review stopped.")
            return
        else:
            print("Please type approve, reject, skip, all, or q.")


if __name__ == "__main__":
    main()
