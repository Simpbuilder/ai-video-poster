from pathlib import Path


TOPICS_FILE = Path("topics.txt")


def read_existing_topics():
    if not TOPICS_FILE.exists():
        TOPICS_FILE.touch()
        return []

    with open(TOPICS_FILE, "r", encoding="utf-8") as topics_file:
        lines = topics_file.readlines()

    topics = []

    for line in lines:
        topic = line.strip()

        if topic:
            topics.append(topic)

    return topics


def add_topic(topic):
    needs_newline = False

    if TOPICS_FILE.exists() and TOPICS_FILE.stat().st_size > 0:
        existing_text = TOPICS_FILE.read_text(encoding="utf-8")

        if not existing_text.endswith("\n"):
            needs_newline = True

    with open(TOPICS_FILE, "a", encoding="utf-8") as topics_file:
        if needs_newline:
            topics_file.write("\n")

        topics_file.write(f"{topic}\n")


def ask_to_clear_topics():
    while True:
        answer = input("Clear existing topics before adding new ones? (y/n): ")
        answer = answer.strip().lower()

        if answer == "y":
            return True

        if answer == "n":
            return False

        print("Please enter y or n.")


def clear_topics_file():
    with open(TOPICS_FILE, "w", encoding="utf-8") as topics_file:
        topics_file.write("")


def get_topics_from_user():
    print("Enter one topic per line.")
    print("Press Enter on an empty line when finished.")

    topics = []

    while True:
        topic = input().strip()

        if not topic:
            break

        topics.append(topic)

    return topics


def print_results(added_topics, duplicate_count, empty_count):
    print()
    print(f"Topics added: {len(added_topics)}")
    print(f"Duplicate topics skipped: {duplicate_count}")

    if empty_count > 0:
        print(f"Empty lines skipped: {empty_count}")

    if not added_topics:
        print("Nothing was added.")
        return

    print("Added topics:")

    for topic in added_topics:
        print(f"- {topic}")


def main():
    existing_topics = read_existing_topics()
    should_clear_topics = ask_to_clear_topics()

    if should_clear_topics:
        clear_topics_file()
        existing_topics = []
        print("Old topics were cleared.")
    else:
        print("Old topics were kept.")

    topics_to_add = get_topics_from_user()
    added_topics = []
    duplicate_count = 0
    empty_count = 0

    for topic in topics_to_add:
        if not topic:
            empty_count += 1
            continue

        if topic in existing_topics:
            duplicate_count += 1
            continue

        add_topic(topic)
        existing_topics.append(topic)
        added_topics.append(topic)

    print_results(added_topics, duplicate_count, empty_count)


if __name__ == "__main__":
    main()
