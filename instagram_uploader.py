import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


PROJECT_FOLDER = Path(__file__).resolve().parent
EXPORTS_FOLDER = PROJECT_FOLDER / "exports"
MEDIA_HISTORY_FILE = PROJECT_FOLDER / "zernio_media_history.json"
POST_HISTORY_FILE = PROJECT_FOLDER / "zernio_post_history.json"
ZERNIO_ACCOUNTS_URL = "https://zernio.com/api/v1/accounts"
ZERNIO_POSTS_URL = "https://zernio.com/api/v1/posts"
ZERNIO_PRESIGN_URL = "https://zernio.com/api/v1/media/presign"
VIDEO_CONTENT_TYPE = "video/mp4"
ACTIVE_POST_STATUSES = {
    "completed",
    "partially-published",
    "partially_published",
    "pending",
    "published",
    "publishing",
    "processing",
    "scheduled",
    "success",
}
VIDEO_REFERENCE_FIELDS = [
    "video_filename",
    "videoFilename",
    "filename",
    "public_url",
    "publicUrl",
    "url",
]
MEDIA_FIELD_NAMES = [
    "mediaItems",
    "media",
    "customMedia",
]


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


def load_json_list(json_path):
    if not json_path.exists():
        return []

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Error: {json_path.name} is not valid JSON.")
        return None

    if not isinstance(data, list):
        print(f"Error: {json_path.name} must contain a list.")
        return None

    return data


def save_json_list(json_path, records):
    json_path.write_text(
        json.dumps(records, indent=4),
        encoding="utf-8",
    )


def print_http_error(error, action):
    response = error.response
    status_code = response.status_code if response is not None else "unknown"

    if status_code == 400:
        print(f"Error: Zernio rejected the {action} payload.")
    elif status_code in [401, 403]:
        print("Error: Zernio authentication failed.")
        print("Check that your ZERNIO_API_KEY is correct.")
    elif status_code == 404:
        print("Error: The Zernio account or endpoint could not be found.")
    elif status_code == 409:
        print("Error: The post may be a duplicate or already exists.")
    elif status_code == 429:
        print("Error: Zernio rate limit was reached.")
        print("Wait a little while, then try again.")
    else:
        print(f"Error: Zernio request failed with status code {status_code}.")
        print(f"The {action} could not be completed.")


def get_json_response(response, description):
    try:
        return response.json()
    except ValueError:
        print(f"Error: Zernio returned invalid JSON for {description}.")
        return None


def fetch_accounts(api_key, requests):
    try:
        response = requests.get(
            ZERNIO_ACCOUNTS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        print_http_error(error, "account list request")
        return None
    except requests.exceptions.RequestException:
        print("Error: Could not connect to Zernio to load accounts.")
        return None

    return get_json_response(response, "the account list")


def fetch_instagram_posts(api_key, requests):
    try:
        response = requests.get(
            ZERNIO_POSTS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            params={
                "platform": "instagram",
                "limit": 100,
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        print_http_error(error, "published posts request")
        return None
    except requests.exceptions.RequestException:
        print("Error: Could not connect to Zernio to load existing posts.")
        return None

    return get_json_response(response, "the published posts list")


def get_list_from_response(data, list_name):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        records = data.get(list_name)

        if isinstance(records, list):
            return records

        nested_data = data.get("data")

        if isinstance(nested_data, dict):
            records = nested_data.get(list_name)

            if isinstance(records, list):
                return records

    print(f"Error: Zernio returned an unexpected {list_name} response format.")
    return None


def get_account_id(account):
    return account.get("id") or account.get("_id")


def normalize_account_id(account_id):
    if not account_id:
        return ""

    return str(account_id).strip().lower()


def get_display_name(account):
    return (
        account.get("displayName")
        or account.get("display_name")
        or account.get("name")
        or "Unknown display name"
    )


def get_username(account):
    return account.get("username") or "Unknown username"


def is_instagram_account(account):
    platform = str(account.get("platform", "")).lower()
    return platform == "instagram"


def is_active_account(account):
    status = account.get("status")

    if isinstance(status, str):
        inactive_statuses = [
            "inactive",
            "disabled",
            "disconnected",
            "expired",
            "error",
        ]
        return status.lower() not in inactive_statuses

    for key in ["active", "isActive", "connected", "isConnected"]:
        if key in account:
            return bool(account.get(key))

    return True


def get_instagram_accounts(accounts):
    instagram_accounts = []

    for account in accounts:
        if not isinstance(account, dict):
            continue

        if not is_instagram_account(account):
            continue

        if not is_active_account(account):
            continue

        if not get_account_id(account):
            continue

        instagram_accounts.append(account)

    return instagram_accounts


def choose_instagram_account(accounts):
    instagram_accounts = get_instagram_accounts(accounts)

    if not instagram_accounts:
        print("No active Instagram accounts were found in Zernio.")
        print("Connect an Instagram account in the Zernio dashboard first.")
        return None

    print("Connected Instagram accounts:")

    for number, account in enumerate(instagram_accounts, start=1):
        print(f"{number}. Display name: {get_display_name(account)}")
        print(f"   Username: {get_username(account)}")
        print(f"   Account ID: {get_account_id(account)}")

    choice = input("Choose one Instagram account by number: ").strip()

    try:
        selected_number = int(choice)
    except ValueError:
        print("Invalid choice. Please enter one number.")
        return None

    if selected_number < 1 or selected_number > len(instagram_accounts):
        print("Invalid choice. Number is not in the list.")
        return None

    return instagram_accounts[selected_number - 1]


def choose_upload_mode():
    print("Choose Instagram upload mode:")
    print("1. Upload one unpublished video")
    print("2. Upload all unpublished videos")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        return "single"

    if choice == "2":
        return "batch"

    print("Invalid choice. Upload canceled.")
    return None


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    return sorted(EXPORTS_FOLDER.glob("*.mp4"))


def normalize_filename(filename):
    return Path(str(filename)).name.lower()


def filename_stem(filename):
    return Path(str(filename)).stem.lower()


def filename_from_url(url):
    try:
        parsed_url = urlparse(str(url))
    except ValueError:
        return ""

    return Path(unquote(parsed_url.path)).name


def value_matches_video(value, video_path):
    if not value:
        return False

    video_filename = normalize_filename(video_path.name)
    video_stem = filename_stem(video_path.name)
    raw_value = str(value)
    raw_filename = normalize_filename(raw_value)

    if raw_filename == video_filename:
        return True

    if filename_stem(raw_filename) == video_stem:
        return True

    url_filename = filename_from_url(raw_value)

    if not url_filename:
        return False

    return (
        normalize_filename(url_filename) == video_filename
        or filename_stem(url_filename) == video_stem
    )


def local_history_says_published(post_history, video_path):
    for record in post_history:
        if not isinstance(record, dict):
            continue

        platform = str(record.get("platform", "")).lower()
        is_not_draft = record.get("is_draft") is False

        if platform != "instagram" or not is_not_draft:
            continue

        if value_matches_video(record.get("video_filename"), video_path):
            return True

        if value_matches_video(record.get("public_url"), video_path):
            return True

    return False


def post_targets_instagram(post):
    platform = str(post.get("platform", "")).lower()

    if platform == "instagram":
        return True

    platforms = post.get("platforms")

    if "platform" not in post and "platforms" not in post:
        return True

    if isinstance(platforms, dict):
        platform = str(platforms.get("platform", "")).lower()
        return platform == "instagram"

    if not isinstance(platforms, list):
        return False

    for platform_item in platforms:
        if isinstance(platform_item, str):
            if platform_item.lower() == "instagram":
                return True

        if isinstance(platform_item, dict):
            item_platform = str(platform_item.get("platform", "")).lower()

            if item_platform == "instagram":
                return True

    return False


def get_platform_entries(post):
    platforms = post.get("platforms")

    if isinstance(platforms, dict):
        return [platforms]

    if isinstance(platforms, list):
        return [
            platform
            for platform in platforms
            if isinstance(platform, dict)
        ]

    return []


def get_platform_account_id(platform_entry):
    return (
        platform_entry.get("accountId")
        or platform_entry.get("account_id")
        or platform_entry.get("id")
        or platform_entry.get("_id")
    )


def platform_entry_targets_instagram(platform_entry):
    platform = str(platform_entry.get("platform", "")).lower()
    return platform in ["", "instagram"]


def get_post_account_id(post):
    account = post.get("account")

    if isinstance(account, dict):
        return get_account_id(account)

    return (
        post.get("accountId")
        or post.get("account_id")
        or account
    )


def post_targets_selected_account(post, selected_account):
    selected_account_id = normalize_account_id(get_account_id(selected_account))
    platform_entries = [
        platform_entry
        for platform_entry in get_platform_entries(post)
        if platform_entry_targets_instagram(platform_entry)
    ]
    matching_account_ids = []

    for platform_entry in platform_entries:
        account_id = normalize_account_id(get_platform_account_id(platform_entry))

        if account_id:
            matching_account_ids.append(account_id)

    top_level_account_id = normalize_account_id(get_post_account_id(post))

    if top_level_account_id:
        matching_account_ids.append(top_level_account_id)

    if matching_account_ids:
        return selected_account_id in matching_account_ids

    if platform_entries:
        return True

    return post_targets_instagram(post)


def post_has_active_publish_status(post):
    status = str(post.get("status", "")).lower()
    return status in ACTIVE_POST_STATUSES


def add_media_items(media_items, possible_items):
    if isinstance(possible_items, list):
        media_items.extend(possible_items)
    elif isinstance(possible_items, dict):
        media_items.append(possible_items)


def get_post_media_items(post):
    media_items = []

    for field_name in MEDIA_FIELD_NAMES:
        add_media_items(media_items, post.get(field_name))

    for platform_entry in get_platform_entries(post):
        for field_name in MEDIA_FIELD_NAMES:
            add_media_items(media_items, platform_entry.get(field_name))

    return media_items


def object_references_video(data, video_path):
    if not isinstance(data, dict):
        return False

    for field_name in VIDEO_REFERENCE_FIELDS:
        if value_matches_video(data.get(field_name), video_path):
            return True

    return False


def post_references_video(post, video_path):
    if object_references_video(post, video_path):
        return True

    for media_item in get_post_media_items(post):
        if object_references_video(media_item, video_path):
            return True

    return False


def zernio_posts_say_published(zernio_posts, video_path, selected_account):
    for post in zernio_posts:
        if not isinstance(post, dict):
            continue

        if not post_targets_instagram(post):
            continue

        if not post_targets_selected_account(post, selected_account):
            continue

        if not post_has_active_publish_status(post):
            continue

        if post_references_video(post, video_path):
            return True

    return False


def get_already_published_reason(
    video_path,
    post_history,
    zernio_posts,
    selected_account,
):
    if local_history_says_published(post_history, video_path):
        return "local history"

    if zernio_posts_say_published(zernio_posts, video_path, selected_account):
        return "Zernio posts"

    return None


def get_unpublished_videos(
    exported_videos,
    post_history,
    zernio_posts,
    selected_account,
):
    unpublished_videos = []
    already_published_count = 0

    for video_path in exported_videos:
        already_published_reason = get_already_published_reason(
            video_path,
            post_history,
            zernio_posts,
            selected_account,
        )

        if already_published_reason:
            already_published_count += 1
            print(
                f"Hidden already-published video: {video_path.name} "
                f"({already_published_reason})"
            )
        else:
            unpublished_videos.append(video_path)

    return unpublished_videos, already_published_count


def choose_video(videos):
    print("Videos available to publish:")

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


def show_batch_video_list(videos):
    print("Videos that will be processed:")
    print(f"Total videos: {len(videos)}")

    for number, video_path in enumerate(videos, start=1):
        print(f"{number}. {video_path.name}")


def choose_batch_pause():
    print("Choose pause between publish requests:")
    print("1. 10 seconds")
    print("2. 30 seconds")
    print("3. 60 seconds")
    print("4. 3 minutes")
    print("5. Custom seconds")

    choice = input("Enter 1, 2, 3, 4, or 5: ").strip()

    if choice == "1":
        return 10

    if choice == "2":
        return 30

    if choice == "3":
        return 60

    if choice == "4":
        return 180

    if choice != "5":
        print("Invalid choice. Upload canceled.")
        return None

    custom_seconds = input("Enter custom pause in seconds: ").strip()

    try:
        pause_seconds = int(custom_seconds)
    except ValueError:
        print("Invalid pause. Please enter a whole number.")
        return None

    if pause_seconds < 10:
        print("Pause must be at least 10 seconds.")
        return None

    return pause_seconds


def confirm_publish_all(pause_seconds):
    print(f"Selected pause between publish requests: {pause_seconds} seconds")
    answer = input("Type PUBLISH ALL to upload and publish all listed videos: ").strip()

    if answer != "PUBLISH ALL":
        print("Batch upload canceled.")
        return False

    return True


def get_line_value(lines, label):
    prefix = f"{label}:"

    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return ""


def read_caption(video_path):
    info_path = video_path.with_suffix(".txt")

    if not info_path.exists():
        print(f"Error: matching upload info file is missing: {info_path.name}")
        return None

    try:
        lines = info_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        print(f"Error: could not read upload info file: {error}")
        return None

    caption = get_line_value(lines, "Suggested caption")
    hashtags = get_line_value(lines, "Suggested hashtags")

    if not caption or not hashtags:
        print("Error: upload info must include Suggested caption and Suggested hashtags.")
        return None

    return f"{caption}\n\n{hashtags}"


def find_existing_media_record(media_history, video_path):
    video_filename = normalize_filename(video_path.name)

    for record in media_history:
        if not isinstance(record, dict):
            continue

        same_filename = normalize_filename(record.get("video_filename", ""))
        public_url = record.get("public_url")

        if same_filename == video_filename and public_url:
            return record

    return None


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
        print_http_error(error, "media presign request")
        return None
    except requests.exceptions.RequestException:
        print("Error: Could not request a Zernio upload URL.")
        return None

    data = get_json_response(response, "the media presign response")

    if not isinstance(data, dict):
        print("Error: Zernio returned an unexpected media presign response format.")
        return None

    if not data.get("uploadUrl") or not data.get("publicUrl"):
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
        print_http_error(error, "media upload request")
        return False
    except requests.exceptions.RequestException:
        print("Error: Could not upload the video to Zernio media storage.")
        return False
    except OSError as error:
        print(f"Error: Could not read the selected video file: {error}")
        return False

    return True


def media_record_exists(media_history, new_record):
    for record in media_history:
        if not isinstance(record, dict):
            continue

        same_filename = (
            normalize_filename(record.get("video_filename", ""))
            == normalize_filename(new_record["video_filename"])
        )
        same_public_url = record.get("public_url") == new_record["public_url"]

        if same_filename and same_public_url:
            return True

    return False


def save_media_record(media_history, new_record):
    if media_record_exists(media_history, new_record):
        return

    media_history.append(new_record)
    save_json_list(MEDIA_HISTORY_FILE, media_history)
    print("Saved media upload result to zernio_media_history.json.")


def make_media_record(video_path, presign_data):
    return {
        "video_filename": video_path.name,
        "public_url": presign_data.get("publicUrl"),
        "zernio_media_key": presign_data.get("key"),
        "media_type": presign_data.get("type"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": video_path.stat().st_size,
    }


def get_or_upload_media(api_key, requests, media_history, video_path):
    existing_record = find_existing_media_record(media_history, video_path)

    if existing_record:
        print("Using existing Zernio media upload record.")
        return existing_record

    print("Uploading video to Zernio media storage.")
    presign_data = request_presigned_upload(api_key, video_path, requests)

    if presign_data is None:
        return None

    upload_succeeded = upload_file_to_presigned_url(
        video_path,
        presign_data["uploadUrl"],
        requests,
    )

    if not upload_succeeded:
        return None

    media_record = make_media_record(video_path, presign_data)
    save_media_record(media_history, media_record)
    print("Media upload succeeded.")

    return media_record


def build_publish_payload(account, media_record, content):
    return {
        "content": content,
        "publishNow": True,
        "platforms": [
            {
                "platform": "instagram",
                "accountId": get_account_id(account),
                "platformSpecificData": {
                    "contentType": "reels",
                },
            },
        ],
        "mediaItems": [
            {
                "type": "video",
                "url": media_record["public_url"],
                "filename": media_record["video_filename"],
                "mimeType": VIDEO_CONTENT_TYPE,
            },
        ],
        "visibility": "public",
    }


def confirm_publish(account, video_path, content):
    print()
    print("Publish preview")
    print("===============")
    print(f"Instagram account: {get_display_name(account)}")
    print(f"Username: {get_username(account)}")
    print(f"Account ID: {get_account_id(account)}")
    print(f"Video filename: {video_path.name}")
    print("Caption:")
    print(content)
    print()
    print("This will upload and publish the Reel publicly on Instagram.")

    answer = input("Type PUBLISH to continue: ").strip()

    if answer != "PUBLISH":
        print("Publish canceled.")
        return False

    return True


def create_instagram_reel_publish(api_key, requests, payload):
    try:
        response = requests.post(
            ZERNIO_POSTS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        print_http_error(error, "publish request")
        return None
    except requests.exceptions.RequestException:
        print("Error: Could not connect to Zernio to publish the Reel.")
        return None

    data = get_json_response(response, "the publish response")

    if not isinstance(data, dict):
        print("Error: Zernio returned an unexpected publish response format.")
        return None

    post = data.get("post")

    if not isinstance(post, dict):
        print("Error: Zernio publish response did not include post details.")
        return None

    return post


def publish_video(
    api_key,
    requests,
    media_history,
    post_history,
    selected_account,
    video_path,
    content,
):
    media_record = get_or_upload_media(
        api_key,
        requests,
        media_history,
        video_path,
    )

    if media_record is None:
        return False

    payload = build_publish_payload(selected_account, media_record, content)
    post = create_instagram_reel_publish(api_key, requests, payload)

    if post is None:
        return False

    save_post_record(
        post_history,
        post,
        selected_account,
        media_record,
        content,
    )

    print("Instagram Reel publish request created.")
    print(f"Post ID: {post.get('_id')}")
    print(f"Status: {post.get('status')}")
    return True


def post_record_exists(post_history, post_id):
    for record in post_history:
        if isinstance(record, dict) and record.get("zernio_post_id") == post_id:
            return True

    return False


def save_post_record(post_history, post, account, media_record, content):
    post_id = post.get("_id")

    if not post_id:
        print("Warning: Zernio did not return a post ID to save.")
        return

    if post_record_exists(post_history, post_id):
        print("This Zernio post is already saved in zernio_post_history.json.")
        return

    post_history.append({
        "zernio_post_id": post_id,
        "status": post.get("status"),
        "platform": "instagram",
        "account_id": get_account_id(account),
        "video_filename": media_record["video_filename"],
        "public_url": media_record["public_url"],
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_draft": False,
        "publish_now": True,
    })
    save_json_list(POST_HISTORY_FILE, post_history)


def run_single_mode(
    api_key,
    requests,
    media_history,
    post_history,
    selected_account,
    unpublished_videos,
):
    selected_video = choose_video(unpublished_videos)

    if selected_video is None:
        return

    content = read_caption(selected_video)

    if content is None:
        return

    if not confirm_publish(selected_account, selected_video, content):
        return

    publish_video(
        api_key,
        requests,
        media_history,
        post_history,
        selected_account,
        selected_video,
        content,
    )


def run_batch_mode(
    api_key,
    requests,
    media_history,
    post_history,
    selected_account,
    unpublished_videos,
    exported_video_count,
    already_published_count,
):
    show_batch_video_list(unpublished_videos)
    pause_seconds = choose_batch_pause()

    if pause_seconds is None:
        return

    if not confirm_publish_all(pause_seconds):
        return

    successful_count = 0
    failed_count = 0
    skipped_caption_count = 0

    for index, video_path in enumerate(unpublished_videos, start=1):
        print()
        print(f"Processing {index} of {len(unpublished_videos)}: {video_path.name}")
        made_publish_request = False

        content = read_caption(video_path)

        if content is None:
            skipped_caption_count += 1
            print(f"Skipped because caption info was missing: {video_path.name}")
        else:
            published = publish_video(
                api_key,
                requests,
                media_history,
                post_history,
                selected_account,
                video_path,
                content,
            )
            made_publish_request = True

            if published:
                successful_count += 1
                print(f"Success: {video_path.name}")
            else:
                failed_count += 1
                print(f"Failed: {video_path.name}")

        if made_publish_request and index < len(unpublished_videos):
            print(f"Waiting {pause_seconds} seconds before the next video.")
            time.sleep(pause_seconds)

    print()
    print("Batch summary")
    print("=============")
    print(f"Videos found: {exported_video_count}")
    print(f"Already published videos skipped: {already_published_count}")
    print(f"Successfully published: {successful_count}")
    print(f"Failed: {failed_count}")
    print(f"Videos skipped because caption info was missing: {skipped_caption_count}")


def main():
    print("Unified Instagram uploader")
    print("==========================")

    upload_mode = choose_upload_mode()

    if upload_mode is None:
        return

    if not load_environment():
        return

    api_key = get_api_key()

    if api_key is None:
        return

    requests = load_requests()

    if requests is None:
        return

    media_history = load_json_list(MEDIA_HISTORY_FILE)

    if media_history is None:
        return

    post_history = load_json_list(POST_HISTORY_FILE)

    if post_history is None:
        return

    accounts_data = fetch_accounts(api_key, requests)

    if accounts_data is None:
        return

    accounts = get_list_from_response(accounts_data, "accounts")

    if accounts is None:
        return

    selected_account = choose_instagram_account(accounts)

    if selected_account is None:
        return

    posts_data = fetch_instagram_posts(api_key, requests)

    if posts_data is None:
        return

    zernio_posts = get_list_from_response(posts_data, "posts")

    if zernio_posts is None:
        return

    exported_videos = find_exported_videos()

    if not exported_videos:
        print("No exported MP4 videos were found in exports/.")
        return

    unpublished_videos, already_published_count = get_unpublished_videos(
        exported_videos,
        post_history,
        zernio_posts,
        selected_account,
    )

    print(f"Exported videos found: {len(exported_videos)}")
    print(f"Already published videos hidden: {already_published_count}")
    print(f"Unpublished videos available: {len(unpublished_videos)}")

    if not unpublished_videos:
        print("All exported videos have already been published to Instagram.")
        return

    if upload_mode == "single":
        run_single_mode(
            api_key,
            requests,
            media_history,
            post_history,
            selected_account,
            unpublished_videos,
        )
    elif upload_mode == "batch":
        run_batch_mode(
            api_key,
            requests,
            media_history,
            post_history,
            selected_account,
            unpublished_videos,
            len(exported_videos),
            already_published_count,
        )


if __name__ == "__main__":
    main()
