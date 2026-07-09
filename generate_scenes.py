import json
from datetime import datetime, timezone
from pathlib import Path

from generators.scene_generator import (
    SceneGenerationError,
    generate_scene_plan,
)


def find_scripts_ready_for_scenes():
    ready_scripts = []
    approval_folder = Path("approval")
    allowed_statuses = [
        "approved",
        "voice_generated",
        "subtitles_generated",
    ]

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        if (
            approval.get("approved") is True
            and approval.get("status") in allowed_statuses
        ):
            ready_scripts.append({
                "path": approval_path,
                "data": approval,
            })

    return ready_scripts


def main():
    ready_scripts = find_scripts_ready_for_scenes()

    if not ready_scripts:
        print("There are no approved scripts ready for scene planning.")
        return

    for ready_script in ready_scripts:
        approval_path = ready_script["path"]
        approval = ready_script["data"]
        topic_folder = approval_path.parent
        scenes_path = topic_folder / "scenes.json"

        if scenes_path.exists():
            print(f"Scene plan already exists for: {approval['topic']}")
            continue

        script_path = topic_folder / "script.txt"

        try:
            script = script_path.read_text(encoding="utf-8")
            scenes = generate_scene_plan(script)
        except FileNotFoundError:
            print(f"Script file is missing for: {approval['topic']}")
            continue
        except SceneGenerationError as error:
            print(
                f"Could not generate scenes for "
                f"'{approval['topic']}': {error}"
            )
            continue

        with open(scenes_path, "w", encoding="utf-8") as scenes_file:
            json.dump(scenes, scenes_file, indent=4)

        approval["scenes_file"] = "scenes.json"
        approval["scenes_generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        with open(approval_path, "w", encoding="utf-8") as approval_file:
            json.dump(approval, approval_file, indent=4)

        print(f"Saved scene plan: {scenes_path}")


if __name__ == "__main__":
    main()
