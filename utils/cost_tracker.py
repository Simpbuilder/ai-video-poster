import csv
from datetime import datetime, timezone
from pathlib import Path


def log_usage(topic, model, usage):
    logs_folder = Path("logs")
    logs_folder.mkdir(parents=True, exist_ok=True)

    costs_file = logs_folder / "costs.csv"
    file_exists = costs_file.exists()

    with open(costs_file, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "topic",
                "model",
                "input_tokens",
                "output_tokens",
                "total_tokens",
            ])

        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            topic,
            model,
            usage.input_tokens,
            usage.output_tokens,
            usage.total_tokens,
        ])
