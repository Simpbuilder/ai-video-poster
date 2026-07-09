from datetime import datetime
from pathlib import Path


def log(message):
    current_time = datetime.now()
    logs_folder = Path("logs")
    logs_folder.mkdir(parents=True, exist_ok=True)

    log_file = logs_folder / f"{current_time:%Y-%m-%d}.log"
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(log_message + "\n")

    print(log_message)
