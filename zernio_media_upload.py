import json
import os
from datetime import datetime, timezone
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
EXPORTS_FOLDER = PROJECT_FOLDER / "exports"
MEDIA_HISTORY_FILE = PROJECT_FOLDER / "zernio_media_history.json"
ZERNIO_PRESIGN_URL = "https://zernio.com/api/v1/media/presign"
VIDEO_CONTENT_TYPE = "video/mp4"


def load_environment():
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Error: python-dotenv is missing.")
        print("Run: py -m pip install -r requirements.txt")
        return False

    load_dotenv()
    return True


def get_api_key():
    api_key = os.getenv("ZERNIO_API_KEY")

    if not api_key:
        print("Error: ZERNIO_API_KEY is missing.")
        print("Add ZERNIO_API_KEY to your .env file and try again.")
        return None

    return api_key


def load_requests():
    try:
        import requests
    except ImportError:
        print("Error: requests is missing.")
        print("Run: py -m pip install -r requirements.txt")
        return None

    return requests


def load_media_history():
    if not MEDIA_HISTORY_FILE.exists():
        return []

    try:
        history = json.loads(MEDIA_HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Error: zernio_media_history.json is not valid JSON.")
        print("No upload was started.")
        return None

    if not isinstance(history, list):
        print("Error: zernio_media_history.json must contain a list.")
        print("No upload was started.")
        return None

    return history


def save_media_history(history):
    MEDIA_HISTORY_FILE.write_text(
        json.dumps(history, indent=4),
        encoding="utf-8",
    )


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    return sorted(EXPORTS_FOLDER.glob("*.mp4"))


def choose_video(videos):
    print("Exported MP4 videos:")

    for number, video_path in enumerate(videos, start=1):
        print(f"{number}. {video_path.name}")

    choice = input("Choose one video by number: ").strip()

    try:
        selected_number = int(choice)
    except ValueError:
        print("Invalid choice. Please enter one number.")
        return None

    if selected_number < 1 or selected_number > len(videos):
        print("Invalid choice. Number is not in the list.")
        return None

    return videos[selected_number - 1]


def confirm_upload(video_path):
    print()
    print(f"This will upload {video_path.name} to Zernio media storage.")
    answer = input("Type UPLOAD to continue: ").strip()

    if answer != "UPLOAD":
        print("Upload canceled.")
        return False

    return True


def print_http_error(error):
    response = error.response
    status_code = response.status_code if response is not None else "unknown"

    if status_code in [401, 403]:
        print("Error: Zernio authentication failed.")
        print("Check that your ZERNIO_API_KEY is correct.")
    elif status_code == 429:
        print("Error: Zernio rate limit was reached.")
        print("Wait a little while, then try again.")
    else:
        print(f"Error: Zernio request failed with status code {status_code}.")
        print("The media upload could not continue.")


def request_presigned_upload(api_key, video_path, requests):
    try:
        response = requests.post(
            ZERNIO_PRESIGN_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "filename": video_path.name,
                "contentType": VIDEO_CONTENT_TYPE,
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        print_http_error(error)
        return None
    except requests.exceptions.RequestException:
        print("Error: Could not request a Zernio upload URL.")
        print("Check your connection and try again.")
        return None

    try:
        data = response.json()
    except ValueError:
        print("Error: Zernio returned a presign response that was not valid JSON.")
        return None

    if not isinstance(data, dict):
        print("Error: Zernio returned an unexpected presign response format.")
        return None

    upload_url = data.get("uploadUrl")
    public_url = data.get("publicUrl")

    if not upload_url or not public_url:
        print("Error: Zernio did not return the required media upload fields.")
        return None

    return data


def upload_file_to_presigned_url(video_path, upload_url, requests):
    try:
        with open(video_path, "rb") as video_file:
            response = requests.put(
                upload_url,
                headers={
                    "Content-Type": VIDEO_CONTENT_TYPE,
                },
                data=video_file,
                timeout=300,
            )
            response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        print_http_error(error)
        return False
    except requests.exceptions.RequestException:
        print("Error: Could not upload the video to Zernio media storage.")
        print("Check your connection and try again.")
        return False
    except OSError as error:
        print(f"Error: Could not read the selected video file: {error}")
        return False

    return True


def make_upload_record(video_path, presign_data):
    return {
        "video_filename": video_path.name,
        "public_url": presign_data.get("publicUrl"),
        "zernio_media_key": presign_data.get("key"),
        "media_type": presign_data.get("type"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": video_path.stat().st_size,
    }


def record_already_exists(history, new_record):
    for record in history:
        same_filename = record.get("video_filename") == new_record["video_filename"]
        same_public_url = record.get("public_url") == new_record["public_url"]

        if same_filename and same_public_url:
            return True

    return False


def save_upload_record(history, new_record):
    if record_already_exists(history, new_record):
        print("This upload record already exists in zernio_media_history.json.")
        return

    history.append(new_record)
    save_media_history(history)
    print("Saved upload result to zernio_media_history.json.")


def main():
    print("Zernio media upload tester")
    print("==========================")

    if not load_environment():
        return

    api_key = get_api_key()

    if api_key is None:
        return

    requests = load_requests()

    if requests is None:
        return

    history = load_media_history()

    if history is None:
        return

    videos = find_exported_videos()

    if not videos:
        print("No exported MP4 videos were found in exports/.")
        return

    selected_video = choose_video(videos)

    if selected_video is None:
        return

    if not confirm_upload(selected_video):
        return

    presign_data = request_presigned_upload(api_key, selected_video, requests)

    if presign_data is None:
        return

    upload_url = presign_data["uploadUrl"]
    upload_succeeded = upload_file_to_presigned_url(
        selected_video,
        upload_url,
        requests,
    )

    if not upload_succeeded:
        return

    upload_record = make_upload_record(selected_video, presign_data)
    save_upload_record(history, upload_record)

    print("Upload succeeded.")
    print(f"Public media URL: {upload_record['public_url']}")


if __name__ == "__main__":
    main()
