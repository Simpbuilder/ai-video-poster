import json
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


PROJECT_FOLDER = Path(__file__).resolve().parent
EXPORTS_FOLDER = PROJECT_FOLDER / "exports"
CLIENT_SECRET_FILE = PROJECT_FOLDER / "client_secret.json"
TOKEN_FILE = PROJECT_FOLDER / "token.json"
UPLOAD_HISTORY_FILE = PROJECT_FOLDER / "youtube_upload_history.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
PRIVACY_STATUS = "public"


def load_upload_history():
    if not UPLOAD_HISTORY_FILE.exists():
        return []

    try:
        return json.loads(UPLOAD_HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Error: youtube_upload_history.json is not valid JSON.")
        sys.exit(1)


def save_upload_history(upload_history):
    UPLOAD_HISTORY_FILE.write_text(
        json.dumps(upload_history, indent=4),
        encoding="utf-8",
    )


def get_uploaded_filenames(upload_history):
    uploaded_filenames = set()

    for upload in upload_history:
        video_filename = upload.get("video_filename")

        if video_filename:
            uploaded_filenames.add(video_filename)

    return uploaded_filenames


def get_line_value(lines, label):
    prefix = f"{label}:"

    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return ""


def read_upload_info(info_path):
    lines = info_path.read_text(encoding="utf-8").splitlines()

    title = get_line_value(lines, "Suggested title")
    caption = get_line_value(lines, "Suggested caption")
    hashtags = get_line_value(lines, "Suggested hashtags")

    missing_fields = []

    if not title:
        missing_fields.append("Suggested title")

    if not caption:
        missing_fields.append("Suggested caption")

    if not hashtags:
        missing_fields.append("Suggested hashtags")

    if missing_fields:
        raise ValueError(
            "Missing fields in upload info file: "
            + ", ".join(missing_fields)
        )

    return {
        "title": title,
        "description": f"{caption}\n\n{hashtags}",
    }


def find_videos_to_upload(uploaded_filenames):
    videos_to_upload = []
    skipped_count = 0

    if not EXPORTS_FOLDER.exists():
        return videos_to_upload, skipped_count

    for video_path in sorted(EXPORTS_FOLDER.glob("*.mp4")):
        info_path = video_path.with_suffix(".txt")

        if video_path.name in uploaded_filenames:
            print(f"Skipped already uploaded video: {video_path.name}")
            skipped_count += 1
            continue

        if not info_path.exists():
            print(f"Skipped missing upload info file: {video_path.name}")
            skipped_count += 1
            continue

        try:
            upload_info = read_upload_info(info_path)
        except ValueError as error:
            print(f"Skipped invalid upload info for {video_path.name}: {error}")
            skipped_count += 1
            continue

        videos_to_upload.append({
            "video_path": video_path,
            "title": upload_info["title"],
            "description": upload_info["description"],
        })

    return videos_to_upload, skipped_count


def ask_for_pause_seconds():
    pause_options = {
        "1": 60,
        "2": 180,
        "3": 600,
        "4": 1800,
        "5": 3600,
    }

    while True:
        print("Choose a pause between uploads:")
        print("1. 1 minute")
        print("2. 3 minutes")
        print("3. 10 minutes")
        print("4. 30 minutes")
        print("5. 60 minutes")
        print("6. Other / custom time")

        choice = input("Choose 1, 2, 3, 4, 5, or 6: ").strip()

        if choice in pause_options:
            return pause_options[choice]

        if choice == "6":
            return ask_for_custom_pause_seconds()

        print("Please choose a number from 1 to 6.")


def ask_for_custom_pause_seconds():
    while True:
        custom_pause = input("Enter custom pause in seconds: ").strip()

        if custom_pause.isdigit():
            return int(custom_pause)

        print("Please enter a whole number.")


def ask_yes_or_no(question):
    answer = input(question).strip().lower()
    return answer == "y"


def print_upload_plan(videos_to_upload, pause_seconds):
    print()
    print("Videos that will be uploaded:")

    for number, video in enumerate(videos_to_upload, start=1):
        print(f"{number}. {video['video_path'].name}")
        print(f"   Title: {video['title']}")

    print()
    print(f"Chosen pause between uploads: {pause_seconds} seconds")
    print(f"Privacy status: {PRIVACY_STATUS}")


def get_youtube_client():
    if not CLIENT_SECRET_FILE.exists():
        print("Error: client_secret.json is missing from the project root.")
        sys.exit(1)

    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=credentials)


def upload_private_video(youtube, video_path, title, description):
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
        },
        "status": {
            "privacyStatus": PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
        },
    }

    media_file = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file,
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            percent = int(status.progress() * 100)
            print(f"Upload progress: {percent}%")

    return response["id"]


def record_successful_upload(upload_history, video_path, video_id, title):
    upload_history.append({
        "video_filename": video_path.name,
        "youtube_video_id": video_id,
        "youtube_link": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "privacy_status": PRIVACY_STATUS,
    })

    save_upload_history(upload_history)


def upload_videos(videos_to_upload, pause_seconds, upload_history):
    uploaded_links = []
    uploaded_count = 0
    failed_count = 0
    youtube = get_youtube_client()

    for index, video in enumerate(videos_to_upload):
        if index > 0:
            print(f"Waiting {pause_seconds} seconds before the next upload.")
            time.sleep(pause_seconds)

        video_path = video["video_path"]
        title = video["title"]
        description = video["description"]

        print()
        print(f"Uploading: {video_path.name}")

        try:
            video_id = upload_private_video(
                youtube,
                video_path,
                title,
                description,
            )
        except Exception as error:
            print(f"Upload failed for {video_path.name}: {error}")
            failed_count += 1
            continue

        video_link = f"https://www.youtube.com/watch?v={video_id}"
        record_successful_upload(
            upload_history,
            video_path,
            video_id,
            title,
        )
        uploaded_links.append(video_link)
        uploaded_count += 1

        print(f"Uploaded successfully: {video_link}")

    return {
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "uploaded_links": uploaded_links,
    }


def print_final_summary(upload_results, skipped_count):
    print()
    print("Final Summary")
    print("=============")
    print(f"Uploaded count: {upload_results['uploaded_count']}")
    print(f"Skipped count: {skipped_count}")
    print(f"Failed count: {upload_results['failed_count']}")

    if upload_results["uploaded_links"]:
        print("Uploaded video links:")

        for link in upload_results["uploaded_links"]:
            print(f"- {link}")


def main():
    print("Batch public YouTube uploader")
    print("==============================")

    upload_history = load_upload_history()
    uploaded_filenames = get_uploaded_filenames(upload_history)
    videos_to_upload, skipped_count = find_videos_to_upload(uploaded_filenames)

    if not videos_to_upload:
        print("No new exported videos with upload info were found.")
        print_final_summary(
            {
                "uploaded_count": 0,
                "failed_count": 0,
                "uploaded_links": [],
            },
            skipped_count,
        )
        return

    pause_seconds = ask_for_pause_seconds()
    print_upload_plan(videos_to_upload, pause_seconds)

    confirmed = ask_yes_or_no(
        "\nUpload all listed videos to YouTube as public? (y/n): "
    )

    if not confirmed:
        print("Upload canceled.")
        return

    upload_results = upload_videos(
        videos_to_upload,
        pause_seconds,
        upload_history,
    )
    print_final_summary(upload_results, skipped_count)


if __name__ == "__main__":
    main()
