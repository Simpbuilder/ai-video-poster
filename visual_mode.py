import json
from pathlib import Path


VISUAL_MODE_FILE = Path("visual_mode.json")


def read_current_mode():
    if not VISUAL_MODE_FILE.exists():
        return None

    try:
        visual_mode = json.loads(
            VISUAL_MODE_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        print("Current visual_mode.json is not valid JSON.")
        return None

    return visual_mode.get("pexels_mode")


def save_visual_mode(pexels_mode):
    visual_mode = {
        "pexels_mode": pexels_mode,
    }

    VISUAL_MODE_FILE.write_text(
        json.dumps(visual_mode, indent=4),
        encoding="utf-8",
    )


def main():
    current_mode = read_current_mode()

    if current_mode:
        print(f"Current Pexels visual mode: {current_mode}")
    else:
        print("Current Pexels visual mode: not set")

    print("Choose Pexels visual mode:")
    print("1. Images")
    print("2. Videos")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        save_visual_mode("images")
        print("Saved Pexels visual mode: images")
    elif choice == "2":
        save_visual_mode("videos")
        print("Saved Pexels visual mode: videos")
    else:
        print("Canceled. visual_mode.json was not changed.")


if __name__ == "__main__":
    main()
