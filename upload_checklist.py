from pathlib import Path


EXPORTS_FOLDER = Path("exports")


def yes_or_no(value):
    if value:
        return "yes"

    return "no"


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    return list(EXPORTS_FOLDER.glob("*.mp4"))


def get_upload_info_value(lines, label):
    for line in lines:
        if line.startswith(label):
            return line.replace(label, "").strip()

    return "Not found"


def read_upload_info(info_path):
    with open(info_path, "r", encoding="utf-8") as info_file:
        lines = info_file.readlines()

    return {
        "title": get_upload_info_value(lines, "Suggested title:"),
        "caption": get_upload_info_value(lines, "Suggested caption:"),
        "hashtags": get_upload_info_value(lines, "Suggested hashtags:"),
    }


def print_summary(exported_videos):
    videos_with_upload_info = 0

    for video_path in exported_videos:
        info_path = video_path.with_suffix(".txt")

        if info_path.exists():
            videos_with_upload_info += 1

    videos_missing_upload_info = len(exported_videos) - videos_with_upload_info

    print("Upload Checklist")
    print("================")
    print(f"Total exported videos: {len(exported_videos)}")
    print(f"Videos with upload info: {videos_with_upload_info}")
    print(f"Videos missing upload info: {videos_missing_upload_info}")


def print_video_details(exported_videos):
    if not exported_videos:
        print()
        print("There are no exported videos yet.")
        return

    print()
    print("Videos")
    print("======")

    for video_path in exported_videos:
        info_path = video_path.with_suffix(".txt")

        print()
        print(f"Video: {video_path.name}")
        print(f"Upload info exists: {yes_or_no(info_path.exists())}")

        if info_path.exists():
            upload_info = read_upload_info(info_path)
            print(f"Suggested title: {upload_info['title']}")
            print(f"Suggested caption: {upload_info['caption']}")
            print(f"Suggested hashtags: {upload_info['hashtags']}")


def main():
    exported_videos = find_exported_videos()

    print_summary(exported_videos)
    print_video_details(exported_videos)


if __name__ == "__main__":
    main()
