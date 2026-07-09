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
|-- generators/           Script, scene, voice, subtitle, and video generators
|-- logs/                 Daily logs and API token usage
|-- output/               Generated scripts and metadata
|-- posted/               Final videos approved for posting
|-- prompts/              Prompts sent to OpenAI
|-- rejected/             Rejected topic folders
|-- utils/                File, logging, and usage helper functions
|-- .env                   OpenAI API key (keep this private)
|-- approve.py            Approves or rejects pending scripts
|-- complete_videos.py    Moves finished videos into completed/
|-- config.py             Project settings
|-- generate_images.py    Creates images from scene plans
|-- generate_scenes.py    Creates scene plans for approved scripts
|-- generate_subtitles.py Creates subtitles for voice-generated scripts
|-- generate_video.py     Creates videos from audio and subtitles
|-- generate_voice.py     Creates audio for approved scripts
|-- main.py               Generates scripts from topics
|-- prepare_voice.py      Lists approved scripts ready for voice generation
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

## Normal Workflow

1. Add one topic per line to `topics.txt`.
2. Run `py run_pipeline.py`.
3. Run `py approve.py`.
4. Choose `approve` or `reject`, then select scripts by number, comma-separated
   numbers, or `all`.
5. Run `py run_pipeline.py` again.
6. Find the completed video at `completed/topic/final.mp4`.
7. Run `py review_videos.py`.
8. Approve, reject, or skip each completed video.

The first pipeline run creates scripts for review. The second pipeline run
continues approved scripts through voice, subtitles, scene planning, image
generation, and video, then moves each finished topic folder into `completed/`.

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
- `metadata.json`: Script details, model information, timestamps, and token
  usage stored in the topic's `output/` folder.
