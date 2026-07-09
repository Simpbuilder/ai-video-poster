import json
from datetime import datetime, timezone
from pathlib import Path

from generators.voice_generator import generate_voice


def find_approved_scripts():
    approved_scripts = []
    approval_folder = Path("approval")

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        if (
            approval.get("approved") is True
            and approval.get("status") == "approved"
        ):
            approved_scripts.append({
                "path": approval_path,
                "data": approval,
            })

    return approved_scripts


def main():
    approved_scripts = find_approved_scripts()

    if not approved_scripts:
        print("There are no approved scripts ready for voice generation.")
        return

    for approved_script in approved_scripts:
        approval_path = approved_script["path"]
        approval = approved_script["data"]
        topic_folder = approval_path.parent
        voice_path = topic_folder / "voice.mp3"

        if voice_path.exists():
            print(f"Voice already exists for: {approval['topic']}")
            continue

        script_path = topic_folder / "script.txt"
        script = script_path.read_text(encoding="utf-8")

        print(f"Generating voice for: {approval['topic']}")

        try:
            generate_voice(script, voice_path)
        except Exception as error:
            print(f"Could not generate voice for '{approval['topic']}': {error}")
            continue

        approval["status"] = "voice_generated"
        approval["voice_file"] = "voice.mp3"
        approval["voice_generated_at"] = datetime.now(timezone.utc).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        print(f"Saved voice: {voice_path}")


if __name__ == "__main__":
    main()
