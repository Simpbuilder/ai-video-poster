import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_FOLDER = Path(__file__).resolve().parent
ENV_FILE = PROJECT_FOLDER / ".env"


def print_check(passed, message):
    status = "OK" if passed else "MISSING"
    print(f"[{status}] {message}")


def check_env_file():
    exists = ENV_FILE.exists()
    print_check(exists, ".env file exists")
    return exists


def check_pexels_api_key():
    api_key = os.getenv("PEXELS_API_KEY")
    exists = bool(api_key)
    print_check(exists, "PEXELS_API_KEY exists")
    return exists


def main():
    print("Pexels setup checklist")
    print("=====================")

    load_dotenv()

    env_file_exists = check_env_file()
    pexels_api_key_exists = check_pexels_api_key()

    print()
    print("Result")
    print("======")

    if env_file_exists and pexels_api_key_exists:
        print("Pexels setup is ready.")
    else:
        print("Pexels setup is not ready yet.")

        if not env_file_exists:
            print("- Create a .env file in the project root.")

        if not pexels_api_key_exists:
            print("- Add PEXELS_API_KEY to your .env file.")


if __name__ == "__main__":
    main()
