import json
from pathlib import Path


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
            script_path = approval_path.parent / "script.txt"
            approved_scripts.append({
                "topic": approval["topic"],
                "script_path": script_path,
            })

    return approved_scripts


def main():
    approved_scripts = find_approved_scripts()

    if not approved_scripts:
        print("There are no approved scripts ready for voice generation.")
        return

    print("Approved scripts:")

    for script in approved_scripts:
        print(f"Topic: {script['topic']}")
        print(f"Script: {script['script_path']}")


if __name__ == "__main__":
    main()
