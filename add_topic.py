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


def main():
    existing_topics = read_existing_topics()

    topic = input("Type a new video topic: ").strip()

    if not topic:
        print("No topic was added because the topic was empty.")
        return

    if topic in existing_topics:
        print("That exact topic already exists in topics.txt.")
        return

    add_topic(topic)
    print(f"Added topic: {topic}")


if __name__ == "__main__":
    main()
