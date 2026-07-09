import json
from datetime import datetime, timezone
from pathlib import Path

from generators.subtitle_generator import generate_subtitles


def find_scripts_ready_for_subtitles():
    ready_scripts = []
    approval_folder = Path("approval")

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        voice_file = approval.get("voice_file")
        voice_path = approval_path.parent / voice_file if voice_file else None

        if (
            approval.get("approved") is True
            and approval.get("status") == "voice_generated"
            and voice_path is not None
            and voice_path.exists()
        ):
            ready_scripts.append({
                "path": approval_path,
                "data": approval,
            })

    return ready_scripts


def main():
    ready_scripts = find_scripts_ready_for_subtitles()

    if not ready_scripts:
        print("There are no voice-generated scripts ready for subtitles.")
        return

    for ready_script in ready_scripts:
        approval_path = ready_script["path"]
        approval = ready_script["data"]
        topic_folder = approval_path.parent
        subtitles_path = topic_folder / "subtitles.srt"

        if subtitles_path.exists():
            print(f"Subtitles already exist for: {approval['topic']}")
            continue

        script_path = topic_folder / "script.txt"
        script = script_path.read_text(encoding="utf-8")

        generate_subtitles(script, subtitles_path)

        approval["status"] = "subtitles_generated"
        approval["subtitles_file"] = "subtitles.srt"
        approval["subtitles_generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        print(f"Saved subtitles: {subtitles_path}")


if __name__ == "__main__":
    main()
