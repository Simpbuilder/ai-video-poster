import json
from datetime import datetime, timezone
from pathlib import Path

illegal_characters = '<>:"/\\|?*'


def read_topics(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            topic = line.strip()
            if topic:
                yield topic


def create_topic_folder(topic):
    safe_name = topic.replace(" ", "_")

    for character in illegal_characters:
        safe_name = safe_name.replace(character, "")

    folder_path = Path("output") / safe_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def save_script(folder_path, script):
    script_path = folder_path / "script.txt"

    with open(script_path, "w", encoding="utf-8") as script_file:
        script_file.write(script)

    return script_path


def save_metadata(folder_path, topic, model, usage):
    metadata = {
        "topic": topic,
        "status": "script_generated",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "script_file": "script.txt",
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }
    metadata_path = folder_path / "metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=4)

    return metadata_path
