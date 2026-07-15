import os


ZERNIO_ACCOUNTS_URL = "https://zernio.com/api/v1/accounts"


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


def fetch_accounts(api_key):
    requests = load_requests()

    if requests is None:
        return None

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
        response = error.response
        status_code = response.status_code if response is not None else "unknown"

        if status_code in [401, 403]:
            print("Error: Zernio authentication failed.")
            print("Check that your ZERNIO_API_KEY is correct.")
        else:
            print(f"Error: Zernio request failed with status code {status_code}.")
            print("The account list could not be loaded.")

        return None
    except requests.exceptions.RequestException:
        print("Error: Could not connect to Zernio.")
        print("Check your internet connection and try again.")
        return None

    try:
        return response.json()
    except ValueError:
        print("Error: Zernio returned a response that was not valid JSON.")
        return None


def get_account_name(account):
    return (
        account.get("name")
        or account.get("username")
        or account.get("displayName")
        or account.get("display_name")
        or "Unknown name"
    )


def print_account(account_number, account):
    platform = account.get("platform", "Unknown platform")
    account_id = account.get("id") or account.get("_id") or "Unknown account id"
    account_name = get_account_name(account)

    print(f"{account_number}. Platform: {platform}")
    print(f"   Name: {account_name}")
    print(f"   Account ID: {account_id}")


def print_unexpected_response_shape(data):
    print("Error: Zernio returned an unexpected response format.")
    print(f"Parsed response type: {type(data).__name__}")

    if isinstance(data, dict):
        top_level_keys = ", ".join(str(key) for key in data.keys())

        if not top_level_keys:
            top_level_keys = "(none)"

        print(f"Top-level JSON keys: {top_level_keys}")


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

    print_unexpected_response_shape(data)
    return None


def print_connected_accounts(data):
    accounts = get_accounts_from_response(data)

    if accounts is None:
        return

    if not accounts:
        print("No Zernio accounts are connected yet.")
        print("Connect an account in the Zernio dashboard, then run this again.")
        return

    print("Connected Zernio accounts:")

    for index, account in enumerate(accounts, start=1):
        if isinstance(account, dict):
            print_account(index, account)
        else:
            print(f"{index}. Unexpected account format: {type(account).__name__}")


def main():
    print("Zernio connected accounts check")
    print("===============================")

    if not load_environment():
        return

    api_key = get_api_key()

    if api_key is None:
        return

    data = fetch_accounts(api_key)

    if data is None:
        return

    print_connected_accounts(data)


if __name__ == "__main__":
    main()
