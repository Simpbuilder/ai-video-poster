import json
from pathlib import Path

from generators.image_generator import generate_image


def find_scene_files():
    scene_files = []

    for folder_name in ["approval", "completed"]:
        folder = Path(folder_name)
        scene_files.extend(folder.rglob("scenes.json"))

    return scene_files


def main():
    scene_files = find_scene_files()

    if not scene_files:
        print("There are no scene plans ready for image generation.")
        return

    for scenes_path in scene_files:
        topic_folder = scenes_path.parent

        try:
            with open(scenes_path, "r", encoding="utf-8") as scenes_file:
                scenes = json.load(scenes_file)
        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read scene plan '{scenes_path}': {error}")
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


if __name__ == "__main__":
    main()
