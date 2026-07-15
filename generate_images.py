import json
import os
import re
import shutil
from io import BytesIO
from pathlib import Path

from config import IMAGE_SIZE


PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
    "you",
    "your",
}


def choose_image_source():
    print("Choose image source:")
    print("1. OpenAI image generation")
    print("2. Pexels stock images")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        return "openai"

    if choice == "2":
        return "pexels"

    print("Image generation canceled. Please enter 1 or 2 next time.")
    return None


def find_scene_files():
    scene_files = []

    for folder_name in ["approval", "completed"]:
        folder = Path(folder_name)
        scene_files.extend(folder.rglob("scenes.json"))

    return scene_files


def load_scenes(scenes_path):
    try:
        with open(scenes_path, "r", encoding="utf-8") as scenes_file:
            return json.load(scenes_file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read scene plan '{scenes_path}': {error}")
        return None


def generate_openai_images(scene_files):
    from generators.image_generator import generate_image

    for scenes_path in scene_files:
        topic_folder = scenes_path.parent
        scenes = load_scenes(scenes_path)

        if scenes is None:
            continue

        for scene in scenes:
            scene_number = scene["scene_number"]
            image_path = topic_folder / f"scene_{scene_number:03}.png"

            if image_path.exists():
                print(f"Image already exists: {image_path}")
                continue

            print(f"Generating image: {image_path}")

            try:
                generate_image(scene["image_prompt"], image_path)
            except Exception as error:
                print(
                    f"Could not generate scene {scene_number} "
                    f"for '{topic_folder.name}': {error}"
                )
                continue

            print(f"Saved image: {image_path}")


def get_pexels_api_key():
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Error: python-dotenv is missing. Run pip install -r requirements.txt.")
        return None

    load_dotenv()
    api_key = os.getenv("PEXELS_API_KEY")

    if not api_key:
        print("Error: PEXELS_API_KEY is missing. Add it to your .env file.")
        return None

    return api_key


def check_pexels_dependencies():
    try:
        import requests  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Error: Pexels image mode needs requests and pillow.")
        print("Run pip install -r requirements.txt and try again.")
        return False

    return True


def get_topic_name(topic_folder):
    approval_path = topic_folder / "approval.json"

    if approval_path.exists():
        try:
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            approval = {}

        topic = approval.get("topic")

        if topic:
            return topic

    return topic_folder.name.replace("_", " ")


def get_scene_text(scene):
    parts = [
        scene.get("narration_text", ""),
        scene.get("visual_description", ""),
        scene.get("image_prompt", ""),
    ]

    return " ".join(parts)


def make_pexels_search_query(topic, scene):
    text = f"{topic} {get_scene_text(scene)}"
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    important_words = []

    for word in words:
        if word in STOP_WORDS or len(word) <= 2:
            continue

        if word not in important_words:
            important_words.append(word)

        if len(important_words) == 6:
            break

    if important_words:
        return " ".join(important_words)

    return topic[:80]


def search_pexels_photos(api_key, query):
    import requests

    response = requests.get(
        PEXELS_SEARCH_URL,
        headers={
            "Authorization": api_key,
        },
        params={
            "query": query,
            "orientation": "portrait",
            "per_page": 10,
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    return data.get("photos", [])


def choose_pexels_photo(photos, used_photo_ids):
    if not photos:
        return None

    for photo in photos:
        photo_id = photo.get("id")

        if photo_id not in used_photo_ids:
            return photo

    return photos[0]


def get_pexels_image_url(photo):
    source = photo.get("src", {})
    return (
        source.get("portrait")
        or source.get("large2x")
        or source.get("large")
        or source.get("original")
    )


def get_target_image_size():
    width_text, height_text = IMAGE_SIZE.split("x")
    return int(width_text), int(height_text)


def download_pexels_image(api_key, image_url, image_path):
    import requests
    from PIL import Image, ImageOps

    response = requests.get(
        image_url,
        headers={
            "Authorization": api_key,
        },
        timeout=60,
    )
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")
    target_size = get_target_image_size()
    image = ImageOps.fit(image, target_size)
    image.save(image_path, "PNG")


def make_pexels_credit(scene_image_filename, photo, search_query):
    return {
        "scene_image_filename": scene_image_filename,
        "pexels_photo_id": photo.get("id"),
        "photographer_name": photo.get("photographer"),
        "photographer_url": photo.get("photographer_url"),
        "photo_page_url": photo.get("url"),
        "original_search_query": search_query,
    }


def load_pexels_credits(topic_folder):
    credits_path = topic_folder / "pexels_credits.json"

    if not credits_path.exists():
        return []

    try:
        credits = json.loads(credits_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Warning: could not read existing credits: {credits_path}")
        return []

    if isinstance(credits, list):
        return credits

    return []


def save_pexels_credits(topic_folder, credits):
    credits_path = topic_folder / "pexels_credits.json"
    credits_path.write_text(
        json.dumps(credits, indent=4),
        encoding="utf-8",
    )


def update_pexels_credit(credits, credit):
    scene_image_filename = credit["scene_image_filename"]
    updated_credits = []
    replaced = False

    for existing_credit in credits:
        if existing_credit.get("scene_image_filename") == scene_image_filename:
            updated_credits.append(credit)
            replaced = True
        else:
            updated_credits.append(existing_credit)

    if not replaced:
        updated_credits.append(credit)

    return updated_credits


def find_credit_for_image(credits, image_filename):
    for credit in credits:
        if credit.get("scene_image_filename") == image_filename:
            return credit

    return None


def reuse_previous_pexels_image(previous_image, image_path):
    shutil.copy(previous_image["image_path"], image_path)
    credit = previous_image["credit"].copy()
    credit["scene_image_filename"] = image_path.name
    return credit


def generate_pexels_images(scene_files):
    if not check_pexels_dependencies():
        return

    api_key = get_pexels_api_key()

    if api_key is None:
        return

    for scenes_path in scene_files:
        topic_folder = scenes_path.parent
        scenes = load_scenes(scenes_path)

        if scenes is None:
            continue

        topic = get_topic_name(topic_folder)
        credits = load_pexels_credits(topic_folder)
        used_photo_ids = {
            credit.get("pexels_photo_id")
            for credit in credits
            if credit.get("pexels_photo_id")
        }
        previous_image = None

        for scene in scenes:
            scene_number = scene["scene_number"]
            image_path = topic_folder / f"scene_{scene_number:03}.png"

            if image_path.exists():
                print(f"Image already exists: {image_path}")
                existing_credit = find_credit_for_image(credits, image_path.name)

                if existing_credit:
                    previous_image = {
                        "image_path": image_path,
                        "credit": existing_credit,
                    }

                continue

            search_query = make_pexels_search_query(topic, scene)
            print(f"Searching Pexels for scene {scene_number}: {search_query}")

            try:
                photos = search_pexels_photos(api_key, search_query)
            except Exception as error:
                print(
                    f"Could not search Pexels for scene {scene_number} "
                    f"for '{topic_folder.name}': {error}"
                )
                continue

            photo = choose_pexels_photo(photos, used_photo_ids)

            if photo is None:
                print(
                    f"Warning: Pexels found no result for scene {scene_number} "
                    f"in '{topic_folder.name}'."
                )

                if previous_image is None:
                    print("No previous Pexels image is available to reuse.")
                    continue

                credit = reuse_previous_pexels_image(previous_image, image_path)
                credit["original_search_query"] = search_query
                credits = update_pexels_credit(credits, credit)
                save_pexels_credits(topic_folder, credits)
                print(f"Reused previous Pexels image: {image_path}")
                continue

            image_url = get_pexels_image_url(photo)

            if not image_url:
                print(
                    f"Warning: Pexels photo has no downloadable image URL "
                    f"for scene {scene_number} in '{topic_folder.name}'."
                )
                continue

            try:
                download_pexels_image(api_key, image_url, image_path)
            except Exception as error:
                print(
                    f"Could not download Pexels image for scene {scene_number} "
                    f"in '{topic_folder.name}': {error}"
                )
                continue

            photo_id = photo.get("id")

            if photo_id:
                used_photo_ids.add(photo_id)

            credit = make_pexels_credit(image_path.name, photo, search_query)
            credits = update_pexels_credit(credits, credit)
            save_pexels_credits(topic_folder, credits)
            previous_image = {
                "image_path": image_path,
                "credit": credit,
            }

            print(f"Saved image: {image_path}")


def main():
    image_source = choose_image_source()

    if image_source is None:
        return

    scene_files = find_scene_files()

    if not scene_files:
        print("There are no scene plans ready for image generation.")
        return

    if image_source == "openai":
        generate_openai_images(scene_files)
    elif image_source == "pexels":
        generate_pexels_images(scene_files)


if __name__ == "__main__":
    main()
