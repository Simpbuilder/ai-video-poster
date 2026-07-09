import json
from datetime import datetime, timezone
from pathlib import Path


def find_pending_scripts():
    pending_scripts = []
    approval_folder = Path("approval")

    for approval_path in approval_folder.rglob("approval.json"):
        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        if (
            approval.get("approved") is False
            and approval.get("status") == "pending_review"
        ):
            pending_scripts.append({
                "path": approval_path,
                "data": approval,
            })

    return pending_scripts


def main():
    pending_scripts = find_pending_scripts()

    if not pending_scripts:
        print("There are no scripts waiting for approval.")
        return

    print("Scripts waiting for approval:")

    for number, script in enumerate(pending_scripts, start=1):
        print(f"{number}. {script['data']['topic']}")

    choice = input("Type the number of the script to approve: ")

    try:
        selected_number = int(choice)
    except ValueError:
        print("Please enter a valid number.")
        return

    if selected_number < 1 or selected_number > len(pending_scripts):
        print("That number is not in the list.")
        return

    selected_script = pending_scripts[selected_number - 1]
    approval = selected_script["data"]
    approval["approved"] = True
    approval["status"] = "approved"
    approval["approved_at"] = datetime.now(timezone.utc).isoformat()

    with open(selected_script["path"], "w", encoding="utf-8") as approval_file:
        json.dump(approval, approval_file, indent=4)

    print(f"Approved: {approval['topic']}")


if __name__ == "__main__":
    main()
