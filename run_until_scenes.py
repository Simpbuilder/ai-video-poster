import subprocess
import sys
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent

PIPELINE_STEPS = [
    "main.py",
    "prepare_voice.py",
    "generate_voice.py",
    "generate_subtitles.py",
    "generate_scenes.py",
]

NEXT_COMMANDS = [
    "python3 approve.py",
    "python3 generate_images.py",
    "python3 generate_video.py",
    "python3 complete_videos.py",
    "python3 review_videos.py",
    "python3 export_videos.py",
]


def run_step(script_name):
    print(f"\nRunning: {script_name}")
    subprocess.run(
        [sys.executable, script_name],
        cwd=PROJECT_FOLDER,
        check=True,
    )


def print_next_commands():
    print("\nNext suggested commands:")
    for command in NEXT_COMMANDS:
        print(command)


def main():
    print("Partial pipeline started. This will stop after scene planning.")

    for script_name in PIPELINE_STEPS:
        try:
            run_step(script_name)
        except subprocess.CalledProcessError:
            print(f"\nPartial pipeline stopped. Step failed: {script_name}")
            sys.exit(1)

    print("\nPartial pipeline finished successfully. Scene planning is complete.")
    print_next_commands()


if __name__ == "__main__":
    main()
