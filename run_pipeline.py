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
    "generate_images.py",
    "generate_video.py",
    "complete_videos.py",
]


def run_step(script_name):
    print(f"\nRunning: {script_name}")
    subprocess.run(
        [sys.executable, script_name],
        cwd=PROJECT_FOLDER,
        check=True,
    )


def print_next_steps():
    print("\nNext steps")
    print("==========")
    print("To approve new scripts, run:")
    print("py approve.py")
    print()
    print("To review finished videos, run:")
    print("py review_videos.py")
    print()
    print("To inspect project progress, run:")
    print("py project_status.py")
    print()
    print("To add another topic, run:")
    print("py add_topic.py")


def main():
    print("Pipeline started.")

    for script_name in PIPELINE_STEPS:
        if script_name == "generate_scenes.py":
            print("\nScene plans will be generated from final subtitle timing.")

        if script_name == "generate_voice.py":
            print("\nOnly approved scripts will continue to voice, subtitles, and video.")

        if script_name == "complete_videos.py":
            print("\nCompleted videos will be moved to completed/.")

        try:
            run_step(script_name)
        except subprocess.CalledProcessError:
            print(f"\nPipeline stopped. Step failed: {script_name}")
            sys.exit(1)

    print("\nPipeline finished successfully.")
    print_next_steps()


if __name__ == "__main__":
    main()
