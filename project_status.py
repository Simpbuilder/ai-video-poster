import json
from pathlib import Path


FOLDER_GROUPS = [
    "approval",
    "completed",
    "posted",
    "rejected",
]

EXPORTS_FOLDER = Path("exports")
UNSAFE_FILENAME_CHARACTERS = '<>:"/\\|?*'


def file_exists(topic_folder, file_name):
    file_path = topic_folder / file_name
    return file_path.exists()


def count_scene_images(topic_folder):
    scene_images = topic_folder.glob("scene_*.png")
    return len(list(scene_images))


def yes_or_no(value):
    if value:
        return "yes"

    return "no"


def make_safe_video_filename(topic):
    safe_name = topic.lower()
    safe_name = safe_name.replace(" ", "-")
    safe_name = safe_name.replace("'", "")
    safe_name = safe_name.replace("\u2019", "")

    for character in UNSAFE_FILENAME_CHARACTERS:
        safe_name = safe_name.replace(character, "")

    return f"{safe_name}.mp4"


def get_export_paths(topic):
    export_file_name = make_safe_video_filename(topic)
    export_mp4_path = EXPORTS_FOLDER / export_file_name
    upload_txt_path = export_mp4_path.with_suffix(".txt")

    return {
        "mp4": export_mp4_path,
        "txt": upload_txt_path,
    }


def find_topics():
    topics = []

    for folder_group in FOLDER_GROUPS:
        group_folder = Path(folder_group)

        if not group_folder.exists():
            continue

        for approval_path in group_folder.rglob("approval.json"):
            topic_folder = approval_path.parent

            with open(approval_path, "r", encoding="utf-8") as approval_file:
                approval = json.load(approval_file)

            topics.append({
                "folder_group": folder_group,
                "topic_folder": topic_folder,
                "approval": approval,
            })

    return topics


def print_summary(topics):
    print("Project Status Overview")
    print("=======================")
    print(f"Total topics: {len(topics)}")

    for folder_group in FOLDER_GROUPS:
        count = 0

        for topic in topics:
            if topic["folder_group"] == folder_group:
                count += 1

        print(f"Topics in {folder_group}: {count}")


def print_topic_details(topics):
    if not topics:
        print()
        print("No topic folders with approval.json were found.")
        return

    print()
    print("Topic Details")
    print("=============")

    for topic in topics:
        topic_folder = topic["topic_folder"]
        approval = topic["approval"]
        topic_name = approval.get("topic", "Unknown topic")
        export_paths = get_export_paths(topic_name)

        print()
        print(f"Folder group: {topic['folder_group']}")
        print(f"Topic: {topic_name}")
        print(f"Status: {approval.get('status', 'Unknown status')}")
        print(f"script.txt: {yes_or_no(file_exists(topic_folder, 'script.txt'))}")
        print(f"voice.mp3: {yes_or_no(file_exists(topic_folder, 'voice.mp3'))}")
        print(f"subtitles.srt: {yes_or_no(file_exists(topic_folder, 'subtitles.srt'))}")
        print(f"scenes.json: {yes_or_no(file_exists(topic_folder, 'scenes.json'))}")
        print(f"Scene images: {count_scene_images(topic_folder)}")
        print(f"final.mp4: {yes_or_no(file_exists(topic_folder, 'final.mp4'))}")
        print(f"Exported mp4: {yes_or_no(export_paths['mp4'].exists())}")
        print(f"Upload txt: {yes_or_no(export_paths['txt'].exists())}")


def main():
    topics = find_topics()

    print_summary(topics)
    print_topic_details(topics)


if __name__ == "__main__":
    main()
