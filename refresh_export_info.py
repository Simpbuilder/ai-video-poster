from pathlib import Path


EXPORTS_FOLDER = Path("exports")
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


def make_topic_from_filename(video_path):
    return video_path.stem.replace("-", " ")


def make_title_from_topic(topic):
    return topic.title()


def make_upload_info(video_path):
    topic = make_topic_from_filename(video_path)
    title = make_title_from_topic(topic)
    caption = (
        f"Ever wondered about this? {topic}. "
        "Quick explanation in under a minute."
    )
    hashtags = get_suggested_hashtags(topic)

    return (
        f"Topic: {topic}\n"
        f"Suggested title: {title}\n"
        f"Suggested caption: {caption}\n"
        f"Suggested hashtags: {hashtags}\n"
        f"Source folder: {video_path.parent}\n"
    )


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    return list(EXPORTS_FOLDER.glob("*.mp4"))


def refresh_upload_info(video_path):
    info_path = video_path.with_suffix(".txt")
    upload_info = make_upload_info(video_path)
    was_created = not info_path.exists()

    with open(info_path, "w", encoding="utf-8") as info_file:
        info_file.write(upload_info)

    if was_created:
        print(f"Created: {info_path}")
        return "created"

    print(f"Updated: {info_path}")
    return "updated"


def main():
    exported_videos = find_exported_videos()
    created_count = 0
    updated_count = 0

    for video_path in exported_videos:
        result = refresh_upload_info(video_path)

        if result == "created":
            created_count += 1
        else:
            updated_count += 1

    print()
    print("Refresh Summary")
    print("===============")
    print(f"Videos found: {len(exported_videos)}")
    print(f"Txt files updated: {updated_count}")
    print(f"Txt files created: {created_count}")


if __name__ == "__main__":
    main()
