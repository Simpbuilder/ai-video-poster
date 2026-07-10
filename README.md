# AI Video Automation

This beginner-friendly Python project turns a list of topics into short vertical
videos.

For each topic, the project can:

1. Generate a YouTube Shorts script with OpenAI.
2. Place the script in an approval queue.
3. Generate voice audio for approved scripts.
4. Create timed subtitles.
5. Create a scene plan from subtitle timing.
6. Generate scene images from the scene plan.
7. Build a vertical video with ffmpeg using voice, subtitles, and scene images.
8. Move the finished topic folder into `completed/`.

Scripts must be approved before scene, voice, subtitle, and video generation
can continue.

## Folder Structure

```text
ai-video-poster/
|-- approval/             Pending and approved topic folders
|-- assets/               Project media assets
|-- completed/            Finished topic folders and videos
|-- exports/              Clean video copies ready for uploading
|-- generators/           Script, scene, voice, subtitle, and video generators
|-- logs/                 Daily logs and API token usage
|-- output/               Generated scripts and metadata
|-- posted/               Final videos approved for posting
|-- prompts/              Prompts sent to OpenAI
|-- rejected/             Rejected topic folders
|-- utils/                File, logging, and usage helper functions
|-- .env                   OpenAI API key (keep this private)
|-- add_topic.py          Adds new topics to topics.txt safely
|-- approve.py            Approves or rejects pending scripts
|-- complete_videos.py    Moves finished videos into completed/
|-- config.py             Project settings
|-- export_videos.py      Copies approved final videos into exports/
|-- generate_images.py    Creates images from scene plans
|-- generate_scenes.py    Creates scene plans for approved scripts
|-- generate_subtitles.py Creates subtitles for voice-generated scripts
|-- generate_video.py     Creates videos from audio and subtitles
|-- generate_voice.py     Creates audio for approved scripts
|-- main.py               Generates scripts from topics
|-- prepare_voice.py      Lists approved scripts ready for voice generation
|-- project_status.py     Shows a read-only overview of project progress
|-- review_videos.py      Approves or rejects completed videos
|-- run_pipeline.py       Runs the automation stages in order
|-- requirements.txt      Python packages used by the project
`-- topics.txt            Topics to process
```

## Setup

### 1. Install Python

Install a recent version of Python 3. During installation on Windows, enable the
option to add Python to `PATH`.

Check that Python is available:

```powershell
py --version
```

### 2. Install ffmpeg

Install ffmpeg and make sure both `ffmpeg` and `ffprobe` are available on your
system `PATH`.

Check the installation:

```powershell
ffmpeg -version
ffprobe -version
```

### 3. Create the `.env` File

Create a file named `.env` in the project root. Add your OpenAI API key:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not share this file or commit your API key to Git.

### 4. Install Python Packages

Open a terminal in the project folder and run:

```powershell
py -m pip install -r requirements.txt
```

## Command Cheat Sheet

On Mac, use `python3` instead of `py`.

```powershell
py add_topic.py
```

Add a new topic safely.

```powershell
py run_pipeline.py
```

Run the automation pipeline.

```powershell
py approve.py
```

Approve or reject generated scripts.

```powershell
py project_status.py
```

Show the current project status.

```powershell
py reset_stage.py
```

Reset a topic back to an earlier generation stage.

```powershell
py review_videos.py
```

Review completed final videos.

```powershell
py export_videos.py
```

Copy approved final videos into `exports/` for uploading.

## Working on PC and Mac

You can work on this project from both your PC and your Mac by using GitHub to
keep the project synced.

Before starting work on either device, run `git pull` so you have the latest
version. After making changes, save your files, commit the changes, and push
them back to GitHub.

Windows uses `py` for Python commands. Mac uses `python3` for Python commands.

The Mac setup currently works for coding, script generation, voice, subtitles,
scene planning, and image generation. Final video rendering currently works
best on the PC because the Mac ffmpeg install had subtitle filter issues. That
Mac rendering issue is parked for later.

For Mac:

```bash
cd ~/Desktop/ai-video-poster
git pull
python3 review_videos.py
```

For PC:

```powershell
cd C:\Users\thecr\Desktop\ai-video-poster
git pull
py review_videos.py
```

## Normal Workflow

1. Add one topic per line to `topics.txt`, or run `py add_topic.py` to add a
   topic safely.
2. Run `py run_pipeline.py`.
3. Run `py approve.py`.
4. Choose `approve` or `reject`, then select scripts by number, comma-separated
   numbers, or `all`.
5. Run `py run_pipeline.py` again.
6. Find the completed video at `completed/topic/final.mp4`.
7. Run `py review_videos.py`.
8. Approve, reject, or skip each completed video.
9. Run `py export_videos.py` to copy approved final videos into `exports/`.

The first pipeline run creates scripts for review. The second pipeline run
continues approved scripts through voice, subtitles, scene planning, image
generation, and video, then moves each finished topic folder into `completed/`.

The `add_topic.py` helper prevents empty topics and exact duplicate topics from
being added to `topics.txt`.

## Project Status

You can check the current state of the project at any time with:

```powershell
py project_status.py
```

This tool scans `approval/`, `completed/`, `posted/`, and `rejected/`. It shows
how many topics are in each folder and whether each topic has files like
`script.txt`, `voice.mp3`, `subtitles.srt`, `scenes.json`, scene images, and
`final.mp4`.

The status tool only reads the project folders. It does not generate anything,
move anything, delete anything, or call any APIs.

## Final Video Review

Completed videos wait in `completed/` until you review them. Start the final
review tool with:

```powershell
py review_videos.py
```

The tool shows each completed video and lets you approve, reject, or skip it.

- Approved final videos move from `completed/` to `posted/`.
- Rejected final videos move from `completed/` to `rejected/`.
- Skipped videos remain in `completed/` for later review.

This tool only organizes reviewed videos. It does not upload or post them.

## Exporting Videos

After final videos are approved, they live in `posted/`. To create clean copies
for uploading, run:

```powershell
py export_videos.py
```

The export tool copies each `final.mp4` from `posted/` into `exports/` using a
clean lowercase filename based on the topic. It skips export files that already
exist.

For each exported video, the tool also creates a matching `.txt` file with the
topic, suggested title, suggested caption, and source folder path. If that
`.txt` file already exists, it is skipped.

The export tool does not move, delete, upload, or post anything.

## Approval Behavior

- Pending scripts are stored in `approval/`.
- Rejected script folders are moved to `rejected/`.
- Approved scripts continue to scene, voice, subtitle, and video generation.
- Finished topic folders are moved from `approval/` to `completed/`.
- Approved final videos are moved to `posted/`.
- Rejected final videos are moved to `rejected/`.
- If a folder name already exists in `completed/`, a suffix such as `_1` or
  `_2` is added.
- The pipeline never runs `approve.py` automatically.

## Configuration

The settings in `config.py` control how the project runs:

- `OPENAI_MODEL`: The OpenAI model used to write scripts.
- `MAX_TOPICS`: The maximum number of topics processed in one run. Use `None`
  to process every topic.
- `SKIP_EXISTING_SCRIPTS`: When `True`, topics that already have `script.txt`
  are skipped.
- `COPY_SCRIPT_TO_APPROVAL`: When `True`, generated scripts are copied into
  the approval queue.
- `VOICE_MODEL`: The OpenAI text-to-speech model used for voice generation.
- `VOICE_NAME`: The voice used for generated speech.
- `IMAGE_MODEL`: The OpenAI image model used for scene images.
- `IMAGE_SIZE`: The generated scene image size.
- `IMAGE_QUALITY`: The generated scene image quality.
- `IMAGE_STYLE`: The global style added to scene image prompts.
- `MAX_IMAGES_PER_RUN`: Safety limit for how many new images can be generated
  in one run. Use `None` to generate all missing images.
- `FORCE_REGENERATE_SCENES`: Allows regenerating `scenes.json` when `True`.
- `FORCE_REGENERATE_VIDEO`: Allows regenerating `final.mp4` when `True`.

## Generated Files

- `script.txt`: The generated YouTube Shorts script.
- `approval.json`: The topic's approval status and processing progress.
- `scenes.json`: The scene plan, narration sections, visual descriptions, image
  prompts, and estimated scene durations.
- `scene_001.png`, `scene_002.png`, etc.: Generated scene images used in the
  final video.
- `voice.mp3`: The generated voice audio.
- `subtitles.srt`: Timed subtitles for the video.
- `final.mp4`: The completed vertical video, stored in its topic folder under
  `completed/`.
- `exports/topic-name.mp4`: A clean copy of an approved final video, ready for
  uploading.
- `exports/topic-name.txt`: Basic upload information for the matching exported
  video.
- `metadata.json`: Script details, model information, timestamps, and token
  usage stored in the topic's `output/` folder.
