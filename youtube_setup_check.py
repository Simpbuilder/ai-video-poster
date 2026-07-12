import importlib
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = PROJECT_FOLDER / "client_secret.json"
EXPORTS_FOLDER = PROJECT_FOLDER / "exports"

REQUIRED_PACKAGES = [
    "googleapiclient",
    "google_auth_oauthlib",
    "google.auth.transport.requests",
]


def print_check(passed, message):
    status = "OK" if passed else "MISSING"
    print(f"[{status}] {message}")


def check_client_secret():
    exists = CLIENT_SECRET_FILE.exists()
    print_check(exists, "client_secret.json exists in the project root")
    return exists


def check_exports_folder():
    exists = EXPORTS_FOLDER.exists()
    print_check(exists, "exports/ folder exists")
    return exists


def find_exported_videos():
    if not EXPORTS_FOLDER.exists():
        return []

    return sorted(EXPORTS_FOLDER.glob("*.mp4"))


def check_exported_videos():
    video_paths = find_exported_videos()
    has_videos = len(video_paths) > 0

    print_check(has_videos, "exports/ contains .mp4 files")

    if video_paths:
        print("Exported videos found:")
        for video_path in video_paths:
            print(f"- {video_path.name}")

    return video_paths


def check_upload_info_files(video_paths):
    if not video_paths:
        print_check(False, "each exported .mp4 has a matching .txt file")
        return False

    missing_info_files = []

    for video_path in video_paths:
        info_path = video_path.with_suffix(".txt")
        if not info_path.exists():
            missing_info_files.append(info_path.name)

    all_present = len(missing_info_files) == 0
    print_check(all_present, "each exported .mp4 has a matching .txt file")

    if missing_info_files:
        print("Missing upload info files:")
        for file_name in missing_info_files:
            print(f"- {file_name}")

    return all_present


def check_required_packages():
    all_present = True

    for package_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package_name)
        except ImportError:
            print_check(False, f"Python package can be imported: {package_name}")
            all_present = False
        else:
            print_check(True, f"Python package can be imported: {package_name}")

    return all_present


def main():
    print("YouTube upload setup checklist")
    print("==============================")

    checks_passed = []

    checks_passed.append(check_client_secret())
    checks_passed.append(check_exports_folder())

    video_paths = check_exported_videos()
    checks_passed.append(len(video_paths) > 0)
    checks_passed.append(check_upload_info_files(video_paths))

    checks_passed.append(check_required_packages())

    print("\nResult")
    print("======")

    if all(checks_passed):
        print("Everything looks ready for the private YouTube uploader.")
    else:
        print("Setup is not ready yet. Fix the missing items listed above.")


if __name__ == "__main__":
    main()
