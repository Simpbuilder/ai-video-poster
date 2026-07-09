import json
import re
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
SEARCH_FOLDERS = [
    PROJECT_FOLDER / "approval",
    PROJECT_FOLDER / "completed",
]

RESET_STAGES = [
    "voice_generated",
    "subtitles_generated",
    "scenes_generated",
    "images_generated",
    "video_generated",
]

SUBTITLE_FIELDS = [
    "subtitles_file",
    "subtitles_generated_at",
]

SCENE_FIELDS = [
    "scenes_file",
    "scenes_generated_at",
]

IMAGE_FIELDS = [
    "image_file",
    "image_files",
    "image_count",
    "images_file",
    "images_generated_at",
    "images_count",
]

VIDEO_FIELDS = [
    "video_file",
    "video_generated_at",
    "completed_at",
]


def read_approval(approval_path):
    with open(approval_path, "r", encoding="utf-8") as approval_file:
        return json.load(approval_file)


def write_approval(approval_path, approval):
    with open(approval_path, "w", encoding="utf-8") as approval_file:
        json.dump(approval, approval_file, indent=4)
        approval_file.write("\n")


def find_topic_folders():
    topic_folders = []

    for search_folder in SEARCH_FOLDERS:
        if not search_folder.exists():
            continue

        for approval_path in search_folder.rglob("approval.json"):
            try:
                approval = read_approval(approval_path)
            except (OSError, json.JSONDecodeError):
                print(f"Could not read: {approval_path}")
                continue

            topic_folders.append({
                "folder": approval_path.parent,
                "approval_path": approval_path,
                "approval": approval,
            })

    return topic_folders


def show_topic_folders(topic_folders):
    print("\nTopic folders found:\n")

    for number, topic_item in enumerate(topic_folders, start=1):
        approval = topic_item["approval"]
        topic = approval.get("topic", "(missing topic)")
        status = approval.get("status", "(missing status)")
        folder = topic_item["folder"]

        print(f"{number}. {topic}")
        print(f"   Status: {status}")
        print(f"   Folder: {folder}")


def choose_topic(topic_folders):
    choice = input("\nSelect one topic by number: ").strip()

    if not choice.isdigit():
        print("Cancelled. Please run the tool again and enter a number.")
        return None

    topic_number = int(choice)

    if topic_number < 1 or topic_number > len(topic_folders):
        print("Cancelled. That number is not in the list.")
        return None

    return topic_folders[topic_number - 1]


def show_reset_stages():
    print("\nReset to which stage?\n")

    for number, stage in enumerate(RESET_STAGES, start=1):
        print(f"{number}. {stage}")


def choose_stage():
    choice = input("\nSelect one stage by number: ").strip()

    if not choice.isdigit():
        print("Cancelled. Please run the tool again and enter a number.")
        return None

    stage_number = int(choice)

    if stage_number < 1 or stage_number > len(RESET_STAGES):
        print("Cancelled. That number is not in the list.")
        return None

    return RESET_STAGES[stage_number - 1]


def is_scene_image(path):
    return re.fullmatch(r"scene_\d+\.png", path.name) is not None


def find_scene_images(topic_folder):
    scene_images = []

    for image_path in topic_folder.glob("scene_*.png"):
        if is_scene_image(image_path):
            scene_images.append(image_path)

    return sorted(scene_images)


def get_files_to_delete(topic_folder, stage):
    files_to_delete = []

    if stage == "voice_generated":
        files_to_delete.append(topic_folder / "subtitles.srt")
        files_to_delete.append(topic_folder / "scenes.json")
        files_to_delete.extend(find_scene_images(topic_folder))
        files_to_delete.append(topic_folder / "final.mp4")

    if stage == "subtitles_generated":
        files_to_delete.append(topic_folder / "scenes.json")
        files_to_delete.extend(find_scene_images(topic_folder))
        files_to_delete.append(topic_folder / "final.mp4")

    if stage == "scenes_generated":
        files_to_delete.extend(find_scene_images(topic_folder))
        files_to_delete.append(topic_folder / "final.mp4")

    if stage == "images_generated":
        files_to_delete.append(topic_folder / "final.mp4")

    return [path for path in files_to_delete if path.exists()]


def get_fields_to_remove(stage):
    fields_to_remove = []

    if stage == "voice_generated":
        fields_to_remove.extend(SUBTITLE_FIELDS)
        fields_to_remove.extend(SCENE_FIELDS)
        fields_to_remove.extend(IMAGE_FIELDS)
        fields_to_remove.extend(VIDEO_FIELDS)

    if stage == "subtitles_generated":
        fields_to_remove.extend(SCENE_FIELDS)
        fields_to_remove.extend(IMAGE_FIELDS)
        fields_to_remove.extend(VIDEO_FIELDS)

    if stage == "scenes_generated":
        fields_to_remove.extend(IMAGE_FIELDS)
        fields_to_remove.extend(VIDEO_FIELDS)

    if stage == "images_generated":
        fields_to_remove.extend(VIDEO_FIELDS)

    return fields_to_remove


def preview_changes(files_to_delete, fields_to_remove, approval, stage):
    existing_fields_to_remove = [
        field for field in fields_to_remove if field in approval
    ]

    print("\nReset preview:\n")

    if files_to_delete:
        print("Files that will be deleted:")
        for file_path in files_to_delete:
            print(f"- {file_path}")
    else:
        print("Files that will be deleted: none")

    if existing_fields_to_remove:
        print("\napproval.json fields that will be removed:")
        for field in existing_fields_to_remove:
            print(f"- {field}")
    else:
        print("\napproval.json fields that will be removed: none")

    print(f"\napproval.json status will be set to: {stage}")


def delete_files(files_to_delete):
    for file_path in files_to_delete:
        file_path.unlink()


def remove_approval_fields(approval, fields_to_remove):
    for field in fields_to_remove:
        approval.pop(field, None)


def reset_topic(topic_item, stage):
    topic_folder = topic_item["folder"]
    approval_path = topic_item["approval_path"]
    approval = topic_item["approval"]
    files_to_delete = get_files_to_delete(topic_folder, stage)
    fields_to_remove = get_fields_to_remove(stage)

    preview_changes(files_to_delete, fields_to_remove, approval, stage)

    confirmation = input("\nType yes to confirm: ").strip()

    if confirmation != "yes":
        print("Cancelled. No files were changed.")
        return

    delete_files(files_to_delete)
    remove_approval_fields(approval, fields_to_remove)
    approval["status"] = stage
    write_approval(approval_path, approval)

    print("\nReset complete.")
    print(f"Topic folder: {topic_folder}")
    print(f"New status: {stage}")


def main():
    topic_folders = find_topic_folders()

    if not topic_folders:
        print("No topic folders with approval.json were found.")
        return

    show_topic_folders(topic_folders)
    topic_item = choose_topic(topic_folders)

    if topic_item is None:
        return

    show_reset_stages()
    stage = choose_stage()

    if stage is None:
        return

    reset_topic(topic_item, stage)


if __name__ == "__main__":
    main()
