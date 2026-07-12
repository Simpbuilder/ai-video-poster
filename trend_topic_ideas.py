import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config import OPENAI_MODEL


PROJECT_FOLDER = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_FOLDER / "topic_ideas.txt"
TOPICS_FILE = PROJECT_FOLDER / "topics.txt"
YOUTUBE_UPLOAD_HISTORY_FILE = PROJECT_FOLDER / "youtube_upload_history.json"

TREND_FEEDS = {
    "United States": "https://trends.google.com/trending/rss?geo=US",
    "United Kingdom": "https://trends.google.com/trending/rss?geo=GB",
    "Australia": "https://trends.google.com/trending/rss?geo=AU",
    "India": "https://trends.google.com/trending/rss?geo=IN",
}

TOPIC_FOLDERS = [
    "approval",
    "completed",
    "posted",
    "rejected",
]


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def fetch_trends_for_region(region_name, feed_url):
    request = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "InfoBuilder topic idea generator"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        rss_data = response.read()

    root = ET.fromstring(rss_data)
    titles = []

    for item in root.findall("./channel/item"):
        title = item.findtext("title")
        if title:
            titles.append(html.unescape(title).strip())

    if not titles:
        raise ValueError("RSS feed returned no trend titles.")

    return titles


def fetch_all_trends():
    all_titles = []
    successful_regions = []

    for region_name, feed_url in TREND_FEEDS.items():
        try:
            titles = fetch_trends_for_region(region_name, feed_url)
        except (urllib.error.URLError, ET.ParseError, ValueError) as error:
            print(f"Warning: could not fetch {region_name} trends: {error}")
            continue

        successful_regions.append(region_name)
        all_titles.extend(titles)

    if not successful_regions:
        raise RuntimeError(
            "Could not fetch trends from any region. Check your internet "
            "connection or try again later."
        )

    print("Successfully fetched trend regions:")
    for region_name in successful_regions:
        print(f"- {region_name}")

    return remove_duplicates(all_titles)


def remove_duplicates(items):
    seen = set()
    unique_items = []

    for item in items:
        normalized_item = normalize_text(item)
        if not normalized_item or normalized_item in seen:
            continue

        seen.add(normalized_item)
        unique_items.append(item)

    return unique_items


def read_topics_file():
    if not TOPICS_FILE.exists():
        return []

    topics = []
    for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines():
        topic = line.strip()
        if topic:
            topics.append(topic)

    return topics


def read_topic_folder_names():
    topics = []

    for folder_name in TOPIC_FOLDERS:
        folder_path = PROJECT_FOLDER / folder_name
        if not folder_path.exists():
            continue

        for child_path in folder_path.iterdir():
            if child_path.is_dir():
                topics.append(child_path.name)

    return topics


def read_exported_video_names():
    exports_folder = PROJECT_FOLDER / "exports"

    if not exports_folder.exists():
        return []

    topics = []
    for video_path in exports_folder.glob("*.mp4"):
        topics.append(video_path.stem)

    return topics


def make_topic_from_video_filename(video_filename):
    video_path = Path(video_filename)
    topic = video_path.stem
    topic = topic.replace("-", " ")
    topic = topic.replace("_", " ")
    return topic


def read_youtube_upload_history_topics():
    if not YOUTUBE_UPLOAD_HISTORY_FILE.exists():
        return []

    try:
        upload_history = json.loads(
            YOUTUBE_UPLOAD_HISTORY_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        print(
            "Warning: youtube_upload_history.json is not valid JSON. "
            "Uploaded video topics will not be checked."
        )
        return []

    if not isinstance(upload_history, list):
        print(
            "Warning: youtube_upload_history.json does not contain a list. "
            "Uploaded video topics will not be checked."
        )
        return []

    topics = []

    for upload in upload_history:
        if not isinstance(upload, dict):
            continue

        video_filename = upload.get("video_filename")
        title = upload.get("title")

        if video_filename:
            topics.append(make_topic_from_video_filename(video_filename))

        if title:
            topics.append(title)

    return topics


def read_existing_topics():
    existing_topics = []
    existing_topics.extend(read_topics_file())
    existing_topics.extend(read_topic_folder_names())
    existing_topics.extend(read_exported_video_names())
    existing_topics.extend(read_youtube_upload_history_topics())
    return remove_duplicates(existing_topics)


def create_openai_client():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to your .env file."
        )

    return OpenAI(api_key=api_key)


def build_prompt(trend_titles, existing_topics):
    topic_request = {
        "trend_titles": trend_titles,
        "existing_topics_to_avoid": existing_topics,
    }

    return (
        "You generate topic ideas for InfoBuilder, a YouTube Shorts channel "
        "that explains educational or interesting ideas for normal people.\n\n"
        "Use the public trend titles as inspiration only. Do not create pure "
        "news headlines, celebrity gossip, political rage bait, or dark and "
        "depressing topics. Avoid duplicates of existing topics.\n\n"
        "Create exactly 20 new topic ideas. Each idea must be internationally "
        "understandable, broad enough for a general audience, and good for a "
        "short educational video. Each idea must start with 'Why ', 'How ', "
        "or 'What happens when '.\n\n"
        "Return only a JSON array of 20 strings. Do not add markdown.\n\n"
        f"{json.dumps(topic_request, indent=2)}"
    )


def parse_topic_ideas(response_text):
    try:
        ideas = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "OpenAI did not return valid JSON topic ideas."
        ) from error

    if not isinstance(ideas, list):
        raise RuntimeError("OpenAI response was not a list of topic ideas.")

    clean_ideas = []
    for idea in ideas:
        if isinstance(idea, str) and idea.strip():
            clean_ideas.append(idea.strip())

    if len(clean_ideas) != 20:
        raise RuntimeError(
            f"Expected 20 topic ideas, but received {len(clean_ideas)}."
        )

    return clean_ideas


def generate_topic_ideas(trend_titles, existing_topics):
    client = create_openai_client()
    prompt = build_prompt(trend_titles, existing_topics)

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    return parse_topic_ideas(response.output_text)


def save_topic_ideas(topic_ideas):
    OUTPUT_FILE.write_text(
        "\n".join(topic_ideas) + "\n",
        encoding="utf-8",
    )


def ask_to_add_to_topics():
    while True:
        answer = input("\nAdd these ideas to topics.txt? (y/n): ")
        answer = answer.strip().lower()

        if answer in ("y", "n"):
            return answer

        print("Please enter y or n.")


def append_ideas_to_topics(topic_ideas):
    existing_topics = read_topics_file()
    existing_topic_keys = {
        normalize_text(topic)
        for topic in existing_topics
    }

    ideas_to_add = []
    duplicate_count = 0

    for idea in topic_ideas:
        idea_key = normalize_text(idea)

        if idea_key in existing_topic_keys:
            duplicate_count += 1
            continue

        existing_topic_keys.add(idea_key)
        ideas_to_add.append(idea)

    if ideas_to_add:
        needs_blank_line = (
            TOPICS_FILE.exists()
            and TOPICS_FILE.stat().st_size > 0
            and not TOPICS_FILE.read_text(encoding="utf-8").endswith("\n")
        )

        with TOPICS_FILE.open("a", encoding="utf-8") as topics_file:
            if needs_blank_line:
                topics_file.write("\n")

            for idea in ideas_to_add:
                topics_file.write(f"{idea}\n")

    return len(ideas_to_add), duplicate_count


def clear_topic_ideas_file():
    OUTPUT_FILE.write_text("", encoding="utf-8")


def handle_topic_ideas_decision(topic_ideas):
    answer = ask_to_add_to_topics()

    if answer == "n":
        print("topics.txt was not changed.")
        print("topic_ideas.txt was kept for later review.")
        return

    added_count, duplicate_count = append_ideas_to_topics(topic_ideas)
    clear_topic_ideas_file()

    print(f"Added ideas: {added_count}")
    print(f"Duplicate ideas skipped: {duplicate_count}")
    print("topic_ideas.txt was cleared.")


def main():
    print("Trend-inspired topic idea generation started.")

    try:
        trend_titles = fetch_all_trends()
    except RuntimeError as error:
        print(f"Error: {error}")
        sys.exit(1)

    existing_topics = read_existing_topics()

    print(f"\nUnique trend titles collected: {len(trend_titles)}")
    print(f"Existing topics checked: {len(existing_topics)}")
    print("\nGenerating 20 new topic ideas with OpenAI...")

    try:
        topic_ideas = generate_topic_ideas(trend_titles, existing_topics)
    except Exception as error:
        print(f"Error: could not generate topic ideas: {error}")
        sys.exit(1)

    save_topic_ideas(topic_ideas)

    print("\nGenerated topic ideas:")
    for idea in topic_ideas:
        print(idea)

    print(f"\nSaved topic ideas to: {OUTPUT_FILE.name}")
    handle_topic_ideas_decision(topic_ideas)


if __name__ == "__main__":
    main()
