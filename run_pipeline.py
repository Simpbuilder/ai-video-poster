import subprocess
import sys
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent

PIPELINE_STEPS = [
    "main.py",
    "prepare_voice.py",
    "generate_voice.py",
    "generate_subtitles.py",
    "generate_video.py",
]


def run_step(script_name):
    print(f"\nRunning: {script_name}")
    subprocess.run(
        [sys.executable, script_name],
        cwd=PROJECT_FOLDER,
        check=True,
    )


def main():
    print("Pipeline started.")

    for script_name in PIPELINE_STEPS:
        if script_name == "generate_voice.py":
            print("\nOnly approved scripts will continue to voice, subtitles, and video.")

        try:
            run_step(script_name)
        except subprocess.CalledProcessError:
            print(f"\nPipeline stopped. Step failed: {script_name}")
            sys.exit(1)

    print("\nPipeline finished successfully.")


if __name__ == "__main__":
    main()
