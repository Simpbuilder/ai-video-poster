import json
import shutil
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


def remove_approved_topics_from_topics_file(approved_topics):
    topics_path = Path("topics.txt")

    if not topics_path.exists():
        return

    approved_topic_set = {
        topic.strip()
        for topic in approved_topics
    }

    original_lines = topics_path.read_text(encoding="utf-8").splitlines()
    remaining_topics = []
    removed_count = 0

    for line in original_lines:
        topic = line.strip()

        if topic in approved_topic_set:
            removed_count += 1
            continue

        remaining_topics.append(topic)

    topics_path.write_text(
        "\n".join(remaining_topics) + ("\n" if remaining_topics else ""),
        encoding="utf-8",
    )

    if removed_count:
        print(f"Removed approved topics from topics.txt: {removed_count}")
    else:
        print("No matching approved topics were removed from topics.txt.")


def get_rejected_folder(source_folder):
    rejected_folder = Path("rejected")
    rejected_folder.mkdir(exist_ok=True)

    destination = rejected_folder / source_folder.name
    suffix = 1

    while destination.exists():
        destination = rejected_folder / f"{source_folder.name}_{suffix}"
        suffix += 1

    return destination


def reject_script(selected_script):
    approval = selected_script["data"]
    approval["approved"] = False
    approval["status"] = "rejected"
    approval["rejected_at"] = datetime.now(timezone.utc).isoformat()

    with open(selected_script["path"], "w", encoding="utf-8") as approval_file:
        json.dump(approval, approval_file, indent=4)

    source_folder = selected_script["path"].parent
    destination = get_rejected_folder(source_folder)
    shutil.move(str(source_folder), str(destination))

    print(f"Rejected: {approval['topic']}")
    print(f"Moved to: {destination}")


def main():
    pending_scripts = find_pending_scripts()

    if not pending_scripts:
        print("There are no scripts waiting for approval.")
        return

    print("Scripts waiting for approval:")

    for number, script in enumerate(pending_scripts, start=1):
        print(f"{number}. {script['data']['topic']}")

    action = input("Type approve or reject: ").strip().lower()

    if action not in ["approve", "reject"]:
        print("Please type approve or reject.")
        return

    choice = input(
        "Type a number, comma-separated numbers, or all: "
    )
    selected_numbers = get_selected_numbers(choice, len(pending_scripts))

    if not selected_numbers:
        print("No valid scripts were selected.")
        return

    approved_topics = []

    for selected_number in selected_numbers:
        selected_script = pending_scripts[selected_number - 1]

        if action == "approve":
            approve_script(selected_script)
            approved_topics.append(selected_script["data"]["topic"])
        else:
            reject_script(selected_script)

    if approved_topics:
        remove_approved_topics_from_topics_file(approved_topics)


if __name__ == "__main__":
    main()
