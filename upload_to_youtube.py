import json
import sys
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
PRIVACY_STATUS = "private"


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
    return {
        upload.get("video_filename")
        for upload in upload_history
        if upload.get("video_filename")
    }


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    videos = []

    for video_path in sorted(EXPORTS_FOLDER.glob("*.mp4")):
        info_path = video_path.with_suffix(".txt")

        if not info_path.exists():
            print(f"Skipped missing upload info file: {video_path.name}")
            continue

        videos.append({
            "video_path": video_path,
            "info_path": info_path,
        })

    return videos


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

    description = f"{caption}\n\n{hashtags}"

    return {
        "title": title,
        "description": description,
    }


def choose_video(videos):
    print("Exported videos ready for upload:")

    for number, video in enumerate(videos, start=1):
        print(f"{number}. {video['video_path'].name}")

    choice = input("Choose a video by number: ").strip()

    try:
        selected_number = int(choice)
    except ValueError:
        print("Invalid choice. Please enter a number.")
        return None

    if selected_number < 1 or selected_number > len(videos):
        print("Invalid choice. Number is not in the list.")
        return None

    return videos[selected_number - 1]


def ask_yes_or_no(question):
    answer = input(question).strip().lower()
    return answer == "y"


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


def main():
    print("Private YouTube uploader")
    print("========================")

    videos = find_exported_videos()

    if not videos:
        print("No exported videos with matching upload info files were found.")
        return

    upload_history = load_upload_history()
    uploaded_filenames = get_uploaded_filenames(upload_history)

    selected_video = choose_video(videos)

    if selected_video is None:
        return

    video_path = selected_video["video_path"]

    if video_path.name in uploaded_filenames:
        duplicate_ok = ask_yes_or_no(
            "This video was already uploaded. Upload it again? (y/n): "
        )

        if not duplicate_ok:
            print("Upload canceled. Duplicate upload was not confirmed.")
            return

    try:
        upload_info = read_upload_info(selected_video["info_path"])
    except ValueError as error:
        print(f"Error: {error}")
        return

    title = upload_info["title"]
    description = upload_info["description"]

    print("\nSelected video:")
    print(f"Filename: {video_path.name}")
    print(f"Title: {title}")
    print("Description:")
    print(description)
    print(f"Privacy status: {PRIVACY_STATUS}")

    confirmed = ask_yes_or_no(
        "\nUpload this video to YouTube as private? (y/n): "
    )

    if not confirmed:
        print("Upload canceled.")
        return

    youtube = get_youtube_client()
    video_id = upload_private_video(youtube, video_path, title, description)
    video_link = f"https://www.youtube.com/watch?v={video_id}"

    record_successful_upload(upload_history, video_path, video_id, title)

    print("\nUpload finished successfully.")
    print(f"YouTube video ID: {video_id}")
    print(f"YouTube link: {video_link}")


if __name__ == "__main__":
    main()
