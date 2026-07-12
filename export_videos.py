import json
import shutil
from pathlib import Path


POSTED_FOLDER = Path("posted")
EXPORTS_FOLDER = Path("exports")
UNSAFE_FILENAME_CHARACTERS = '<>:"/\\|?*'
BASE_HASHTAGS = [
    "#shorts",
    "#explained",
    "#didyouknow",
]

HASHTAG_CATEGORIES = [
    {
        "keywords": [
            "car",
            "engine",
            "turbo",
            "brake",
            "driving",
            "electric car",
        ],
        "hashtags": ["#cars", "#cartok", "#engineering", "#carfacts"],
    },
    {
        "keywords": [
            "brain",
            "memory",
            "dream",
            "psychology",
            "people",
            "human",
        ],
        "hashtags": ["#psychology", "#brain", "#humanbehavior", "#facts"],
    },
    {
        "keywords": [
            "phone",
            "battery",
            "screen",
            "tech",
            "internet",
            "ai",
        ],
        "hashtags": ["#tech", "#technology", "#howitworks", "#facts"],
    },
    {
        "keywords": [
            "food",
            "spicy",
            "caffeine",
            "energy drink",
            "water",
        ],
        "hashtags": ["#foodfacts", "#science", "#bodyfacts"],
    },
    {
        "keywords": [
            "animal",
            "cat",
            "dog",
            "bird",
            "shark",
            "fish",
        ],
        "hashtags": ["#animals", "#animalfacts", "#nature"],
    },
    {
        "keywords": [
            "money",
            "card",
            "price",
            "buying",
            "expensive",
        ],
        "hashtags": ["#money", "#psychology", "#financefacts"],
    },
]

GENERAL_HASHTAGS = ["#facts", "#learnsomething", "#curiosity"]
MAX_HASHTAGS = 8


def make_safe_video_filename(topic):
    safe_name = topic.lower()
    safe_name = safe_name.replace(" ", "-")
    safe_name = safe_name.replace("'", "")
    safe_name = safe_name.replace("\u2019", "")

    for character in UNSAFE_FILENAME_CHARACTERS:
        safe_name = safe_name.replace(character, "")

    return f"{safe_name}.mp4"


def add_hashtag(hashtags, hashtag):
    hashtag = hashtag.lower()

    if hashtag not in hashtags and len(hashtags) < MAX_HASHTAGS:
        hashtags.append(hashtag)


def get_suggested_hashtags(topic):
    topic_text = topic.lower()
    hashtags = []
    matched_category = False

    for hashtag in BASE_HASHTAGS:
        add_hashtag(hashtags, hashtag)

    for category in HASHTAG_CATEGORIES:
        has_matching_keyword = any(
            keyword in topic_text
            for keyword in category["keywords"]
        )

        if not has_matching_keyword:
            continue

        matched_category = True

        for hashtag in category["hashtags"]:
            add_hashtag(hashtags, hashtag)

    if not matched_category:
        for hashtag in GENERAL_HASHTAGS:
            add_hashtag(hashtags, hashtag)

    return " ".join(hashtags)


def find_posted_videos():
    posted_videos = []

    if not POSTED_FOLDER.exists():
        return posted_videos

    for approval_path in POSTED_FOLDER.rglob("approval.json"):
        video_path = approval_path.parent / "final.mp4"

        if not video_path.exists():
            continue

        with open(approval_path, "r", encoding="utf-8") as approval_file:
            approval = json.load(approval_file)

        topic = approval.get("topic", "untitled video")
        status = approval.get("status", "unknown")

        if status != "approved_final":
            print(f"Skipped: {topic}")
            print(f"Status is not approved_final: {status}")
            continue

        posted_videos.append({
            "topic": topic,
            "video_path": video_path,
            "source_folder": approval_path.parent,
        })

    return posted_videos


def write_upload_info_file(video, export_path):
    info_path = export_path.with_suffix(".txt")

    if info_path.exists():
        print(f"Upload info already exists: {info_path}")
        return

    topic = video["topic"]
    suggested_hashtags = get_suggested_hashtags(topic)
    upload_info = (
        f"Topic: {topic}\n"
        f"Suggested title: {topic}\n"
        f"Suggested caption: Ever wondered about this? {topic}. "
        "Quick explanation in under a minute.\n"
        f"Suggested hashtags: {suggested_hashtags}\n"
        f"Source folder path: {video['source_folder']}\n"
    )

    with open(info_path, "w", encoding="utf-8") as info_file:
        info_file.write(upload_info)

    print(f"Created upload info: {info_path}")


def export_video(video):
    EXPORTS_FOLDER.mkdir(exist_ok=True)

    file_name = make_safe_video_filename(video["topic"])
    export_path = EXPORTS_FOLDER / file_name

    if export_path.exists():
        print(f"Skipped: {video['topic']}")
        print(f"Already exists: {export_path}")
    else:
        shutil.copy(video["video_path"], export_path)

        print(f"Exported: {video['topic']}")
        print(f"Saved to: {export_path}")

    write_upload_info_file(video, export_path)


def main():
    posted_videos = find_posted_videos()

    if not posted_videos:
        print("There are no posted videos ready to export.")
        return

    for video in posted_videos:
        export_video(video)


if __name__ == "__main__":
    main()
