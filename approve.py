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


def get_selected_numbers(choice, number_of_scripts):
    if choice.strip().lower() == "all":
        return list(range(1, number_of_scripts + 1))

    selected_numbers = []

    for value in choice.split(","):
        value = value.strip()

        try:
            number = int(value)
        except ValueError:
            print(f"Ignoring invalid number: {value}")
            continue

        if number < 1 or number > number_of_scripts:
            print(f"Number {number} is not in the list.")
            continue

        if number not in selected_numbers:
            selected_numbers.append(number)

    return selected_numbers


def approve_script(selected_script):
    approval = selected_script["data"]
    approval["approved"] = True
    approval["status"] = "approved"
    approval["approved_at"] = datetime.now(timezone.utc).isoformat()

    with open(selected_script["path"], "w", encoding="utf-8") as approval_file:
        json.dump(approval, approval_file, indent=4)

    print(f"Approved: {approval['topic']}")


def main():
    pending_scripts = find_pending_scripts()

    if not pending_scripts:
        print("There are no scripts waiting for approval.")
        return

    print("Scripts waiting for approval:")

    for number, script in enumerate(pending_scripts, start=1):
        print(f"{number}. {script['data']['topic']}")

    choice = input(
        "Type a number, comma-separated numbers, or all: "
    )
    selected_numbers = get_selected_numbers(choice, len(pending_scripts))

    if not selected_numbers:
        print("No valid scripts were selected.")
        return

    for selected_number in selected_numbers:
        selected_script = pending_scripts[selected_number - 1]
        approve_script(selected_script)


if __name__ == "__main__":
    main()
