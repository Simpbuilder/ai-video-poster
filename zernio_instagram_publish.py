import json
import os
from datetime import datetime, timezone
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
EXPORTS_FOLDER = PROJECT_FOLDER / "exports"
MEDIA_HISTORY_FILE = PROJECT_FOLDER / "zernio_media_history.json"
POST_HISTORY_FILE = PROJECT_FOLDER / "zernio_post_history.json"
ZERNIO_ACCOUNTS_URL = "https://zernio.com/api/v1/accounts"
ZERNIO_POSTS_URL = "https://zernio.com/api/v1/posts"
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


def load_json_list(json_path, missing_message):
    if not json_path.exists():
        print(missing_message)
        return None

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Error: {json_path.name} is not valid JSON.")
        return None

    if not isinstance(data, list):
        print(f"Error: {json_path.name} must contain a list.")
        return None

    return data


def load_media_history():
    return load_json_list(
        MEDIA_HISTORY_FILE,
        "Error: zernio_media_history.json is missing. Upload media first.",
    )


def load_post_history():
    if not POST_HISTORY_FILE.exists():
        return []

    return load_json_list(
        POST_HISTORY_FILE,
        "Error: zernio_post_history.json is missing.",
    )


def save_post_history(history):
    POST_HISTORY_FILE.write_text(
        json.dumps(history, indent=4),
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


def get_accounts_from_response(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        accounts = data.get("accounts")

        if isinstance(accounts, list):
            return accounts

        nested_data = data.get("data")

        if isinstance(nested_data, dict):
            accounts = nested_data.get("accounts")

            if isinstance(accounts, list):
                return accounts

    print("Error: Zernio returned an unexpected accounts response format.")
    return None


def get_account_id(account):
    return account.get("id") or account.get("_id")


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


def get_uploaded_video_records(media_history):
    records = []

    for record in media_history:
        if not isinstance(record, dict):
            continue

        if not record.get("video_filename") or not record.get("public_url"):
            continue

        records.append(record)

    return records


def split_unpublished_and_published_records(media_history, post_history):
    records = get_uploaded_video_records(media_history)
    unpublished_records = []
    published_count = 0

    for record in records:
        already_published = has_existing_non_draft_instagram_post(
            post_history,
            record["video_filename"],
        )

        if already_published:
            published_count += 1
        else:
            unpublished_records.append(record)

    return unpublished_records, published_count


def choose_uploaded_video(media_history, post_history):
    records, published_count = split_unpublished_and_published_records(
        media_history,
        post_history,
    )

    if not records and published_count == 0:
        print("No uploaded Zernio video records were found.")
        return None

    print(f"Unpublished videos available: {len(records)}")
    print(f"Already published videos hidden: {published_count}")

    if not records:
        print("All uploaded Zernio videos have already been published to Instagram.")
        return None

    print("Uploaded Zernio videos:")

    for number, record in enumerate(records, start=1):
        print(f"{number}. Filename: {record['video_filename']}")
        print(f"   Uploaded at: {record.get('uploaded_at', 'Unknown time')}")
        print(f"   Public URL: {record['public_url']}")

    choice = input("Choose one uploaded video by number: ").strip()

    try:
        selected_number = int(choice)
    except ValueError:
        print("Invalid choice. Please enter one number.")
        return None

    if selected_number < 1 or selected_number > len(records):
        print("Invalid choice. Number is not in the list.")
        return None

    return records[selected_number - 1]


def get_line_value(lines, label):
    prefix = f"{label}:"

    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return ""


def read_caption_from_export_info(video_filename):
    info_path = EXPORTS_FOLDER / f"{Path(video_filename).stem}.txt"

    if not info_path.exists():
        return None

    try:
        lines = info_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    caption = get_line_value(lines, "Suggested caption")
    hashtags = get_line_value(lines, "Suggested hashtags")

    if not caption or not hashtags:
        return None

    return f"{caption}\n\n{hashtags}"


def ask_for_manual_caption():
    caption = input("Enter the Instagram caption manually: ").strip()

    if not caption:
        print("Caption is empty. Publish canceled.")
        return None

    return caption


def get_caption(video_filename):
    caption = read_caption_from_export_info(video_filename)

    if caption:
        return caption

    print("Could not read matching caption info from exports/.")
    return ask_for_manual_caption()


def build_publish_payload(account, video_record, content):
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
                "url": video_record["public_url"],
                "filename": video_record["video_filename"],
                "mimeType": VIDEO_CONTENT_TYPE,
            },
        ],
        "visibility": "public",
    }


def confirm_publish(account, video_record, content):
    print()
    print("Publish preview")
    print("===============")
    print(f"Instagram account: {get_display_name(account)}")
    print(f"Username: {get_username(account)}")
    print(f"Account ID: {get_account_id(account)}")
    print(f"Video filename: {video_record['video_filename']}")
    print("Caption:")
    print(content)
    print()
    print("This will publish the Reel publicly on Instagram.")

    answer = input("Type PUBLISH to continue: ").strip()

    if answer != "PUBLISH":
        print("Publish canceled.")
        return False

    return True


def has_existing_non_draft_instagram_post(post_history, video_filename):
    for record in post_history:
        if not isinstance(record, dict):
            continue

        same_video = record.get("video_filename") == video_filename
        is_instagram = record.get("platform") == "instagram"
        is_not_draft = record.get("is_draft") is False

        if same_video and is_instagram and is_not_draft:
            return True

    return False


def confirm_duplicate_publish(video_filename):
    print()
    print(f"Warning: {video_filename} already has a non-draft Instagram record.")
    answer = input("Type PUBLISH AGAIN to continue: ").strip()

    if answer != "PUBLISH AGAIN":
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


def post_record_exists(post_history, post_id):
    for record in post_history:
        if isinstance(record, dict) and record.get("zernio_post_id") == post_id:
            return True

    return False


def save_post_record(post_history, post, account, video_record, content):
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
        "video_filename": video_record["video_filename"],
        "public_url": video_record["public_url"],
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_draft": False,
        "publish_now": True,
    })
    save_post_history(post_history)


def main():
    print("Zernio Instagram Reel publisher")
    print("===============================")

    if not load_environment():
        return

    api_key = get_api_key()

    if api_key is None:
        return

    requests = load_requests()

    if requests is None:
        return

    media_history = load_media_history()

    if media_history is None:
        return

    post_history = load_post_history()

    if post_history is None:
        return

    accounts_data = fetch_accounts(api_key, requests)

    if accounts_data is None:
        return

    accounts = get_accounts_from_response(accounts_data)

    if accounts is None:
        return

    selected_account = choose_instagram_account(accounts)

    if selected_account is None:
        return

    selected_video = choose_uploaded_video(media_history, post_history)

    if selected_video is None:
        return

    content = get_caption(selected_video["video_filename"])

    if content is None:
        return

    if not confirm_publish(selected_account, selected_video, content):
        return

    already_published = has_existing_non_draft_instagram_post(
        post_history,
        selected_video["video_filename"],
    )

    if already_published:
        if not confirm_duplicate_publish(selected_video["video_filename"]):
            return

    payload = build_publish_payload(selected_account, selected_video, content)
    post = create_instagram_reel_publish(api_key, requests, payload)

    if post is None:
        return

    save_post_record(
        post_history,
        post,
        selected_account,
        selected_video,
        content,
    )

    print("Instagram Reel publish request created.")
    print(f"Post ID: {post.get('_id')}")
    print(f"Status: {post.get('status')}")


if __name__ == "__main__":
    main()
