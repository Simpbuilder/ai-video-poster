import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
ARCHIVE_FOLDER = PROJECT_FOLDER / "archive"
ARCHIVE_FILE = ARCHIVE_FOLDER / "finished_topics.json"
YOUTUBE_UPLOAD_HISTORY_FILE = PROJECT_FOLDER / "youtube_upload_history.json"

TARGET_FOLDER_NAMES = [
    "exports",
    "output",
    "posted",
    "approval",
]


def ask_for_confirmation():
    print(
        "This will archive finished topics and delete generated files from "
        "exports/, output/, posted/, and approval/."
    )
    print("Folders that will be cleared:")

    for folder_name in TARGET_FOLDER_NAMES:
        print(f"- {folder_name}/")

    answer = input("Type CLEAR to continue: ")
    return answer == "CLEAR"


def load_archive():
    if not ARCHIVE_FILE.exists():
        return {
            "finished_topics": [],
        }

    try:
        archive = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Error: archive/finished_topics.json is not valid JSON.")
        print("Cleanup canceled. Nothing was deleted.")
        return None

    if isinstance(archive, list):
        return {
            "finished_topics": archive,
        }

    if not isinstance(archive, dict):
        print("Error: archive/finished_topics.json has an unexpected format.")
        print("Cleanup canceled. Nothing was deleted.")
        return None

    if "finished_topics" not in archive:
        archive["finished_topics"] = []

    if not isinstance(archive["finished_topics"], list):
        print("Error: archive/finished_topics.json has an unexpected format.")
        print("Cleanup canceled. Nothing was deleted.")
        return None

    return archive


def load_youtube_upload_history():
    if not YOUTUBE_UPLOAD_HISTORY_FILE.exists():
        return []

    try:
        upload_history = json.loads(
            YOUTUBE_UPLOAD_HISTORY_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        print("Warning: youtube_upload_history.json is not valid JSON.")
        print("YouTube upload details will not be added to the archive.")
        return []

    if not isinstance(upload_history, list):
        print("Warning: youtube_upload_history.json does not contain a list.")
        print("YouTube upload details will not be added to the archive.")
        return []

    return upload_history


def get_upload_history_by_filename(upload_history):
    upload_history_by_filename = {}

    for upload in upload_history:
        if not isinstance(upload, dict):
            continue

        video_filename = upload.get("video_filename")

        if video_filename:
            upload_history_by_filename[video_filename] = upload

    return upload_history_by_filename


def read_json_file(json_path):
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Warning: could not read JSON file: {json_path}")
        return {}


def collect_posted_topic_entries():
    posted_folder = PROJECT_FOLDER / "posted"
    entries = []

    if not posted_folder.exists():
        return entries

    for topic_folder in posted_folder.iterdir():
        if not topic_folder.is_dir():
            continue

        approval_path = topic_folder / "approval.json"
        approval = {}

        if approval_path.exists():
            approval = read_json_file(approval_path)

        script_path = topic_folder / "script.txt"
        topic = approval.get("topic", topic_folder.name)
        status = approval.get("status", "unknown")
        script_value = str(script_path) if script_path.exists() else topic_folder.name

        entries.append({
            "archive_key": f"posted:{topic_folder.name}",
            "archive_type": "posted_topic",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "topic": topic,
            "status": status,
            "script_path": script_value,
            "posted_folder_name": topic_folder.name,
            "final_mp4_exists": (topic_folder / "final.mp4").exists(),
        })

    return entries


def collect_export_video_entries(upload_history_by_filename):
    exports_folder = PROJECT_FOLDER / "exports"
    entries = []

    if not exports_folder.exists():
        return entries

    for video_path in exports_folder.glob("*.mp4"):
        info_path = video_path.with_suffix(".txt")
        upload = upload_history_by_filename.get(video_path.name, {})

        entry = {
            "archive_key": f"export:{video_path.name}",
            "archive_type": "export_video",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "export_video_filename": video_path.name,
            "upload_info_filename": info_path.name if info_path.exists() else None,
        }

        if upload:
            entry["youtube_video_id"] = upload.get("youtube_video_id")
            entry["youtube_link"] = upload.get("youtube_link")
            entry["title"] = upload.get("title")
            entry["privacy_status"] = upload.get("privacy_status")

        entries.append(entry)

    return entries


def get_archive_key(entry):
    archive_key = entry.get("archive_key")

    if archive_key:
        return archive_key

    if entry.get("archive_type") == "posted_topic":
        return f"posted:{entry.get('posted_folder_name')}"

    if entry.get("archive_type") == "export_video":
        return f"export:{entry.get('export_video_filename')}"

    return None


def append_new_archive_entries(archive, new_entries):
    existing_keys = set()

    for entry in archive["finished_topics"]:
        archive_key = get_archive_key(entry)

        if archive_key:
            existing_keys.add(archive_key)

    added_count = 0

    for entry in new_entries:
        archive_key = get_archive_key(entry)

        if archive_key in existing_keys:
            continue

        archive["finished_topics"].append(entry)
        existing_keys.add(archive_key)
        added_count += 1

    return added_count


def save_archive(archive):
    ARCHIVE_FOLDER.mkdir(exist_ok=True)
    ARCHIVE_FILE.write_text(
        json.dumps(archive, indent=4),
        encoding="utf-8",
    )


def delete_folder_contents(folder_path):
    files_deleted = 0
    folders_deleted = 0

    for child_path in folder_path.iterdir():
        if child_path.name == ".gitkeep":
            continue

        if child_path.is_dir():
            shutil.rmtree(child_path)
            folders_deleted += 1
            print(f"Deleted folder: {child_path}")
        else:
            child_path.unlink()
            files_deleted += 1
            print(f"Deleted file: {child_path}")

    return files_deleted, folders_deleted


def clear_target_folders():
    total_files_deleted = 0
    total_folders_deleted = 0
    folders_skipped = 0

    for folder_name in TARGET_FOLDER_NAMES:
        folder_path = PROJECT_FOLDER / folder_name

        if not folder_path.exists():
            print(f"Skipped missing folder: {folder_path}")
            folders_skipped += 1
            continue

        files_deleted, folders_deleted = delete_folder_contents(folder_path)
        total_files_deleted += files_deleted
        total_folders_deleted += folders_deleted

    return {
        "files_deleted": total_files_deleted,
        "folders_deleted": total_folders_deleted,
        "folders_skipped": folders_skipped,
    }


def print_final_summary(archive_entries_added, cleanup_summary):
    print()
    print("Cleanup Summary")
    print("===============")
    print(f"Archive entries added: {archive_entries_added}")
    print(f"Files deleted: {cleanup_summary['files_deleted']}")
    print(f"Folders deleted: {cleanup_summary['folders_deleted']}")
    print(f"Folders skipped: {cleanup_summary['folders_skipped']}")


def main():
    if not ask_for_confirmation():
        print("Cleanup canceled. Nothing was deleted.")
        return

    archive = load_archive()

    if archive is None:
        return

    upload_history = load_youtube_upload_history()
    upload_history_by_filename = get_upload_history_by_filename(upload_history)

    new_entries = []
    new_entries.extend(collect_posted_topic_entries())
    new_entries.extend(collect_export_video_entries(upload_history_by_filename))

    archive_entries_added = append_new_archive_entries(archive, new_entries)
    save_archive(archive)

    print(f"Archive entries added: {archive_entries_added}")

    cleanup_summary = clear_target_folders()
    print_final_summary(archive_entries_added, cleanup_summary)


if __name__ == "__main__":
    main()
