# AI Video Poster - Project State

## Current goal
Build a Python automation pipeline that turns topics into short vertical videos.

## Current workflow
1. Add topics to topics.txt
2. Run py run_pipeline.py on Windows or python3 run_pipeline.py on Mac
3. Approve scripts with approve.py
4. Run pipeline again
5. Review completed videos with review_videos.py

## Pipeline order
main.py
prepare_voice.py
generate_voice.py
generate_subtitles.py
generate_scenes.py
generate_images.py
generate_video.py
complete_videos.py

## Important behavior
- approve.py is manual and not part of run_pipeline.py
- completed videos go to completed/
- review_videos.py moves approved final videos to posted/
- rejected scripts/videos go to rejected/
- generated images are scene_001.png, scene_002.png, etc.
- video generation uses scenes.json and scene images
- black gaps between scenes and at the end were fixed
- image style should stay clean educational/editorial, not photorealistic or aggressive comic style

## Important config settings
- MAX_TOPICS
- IMAGE_STYLE
- MAX_IMAGES_PER_RUN
- FORCE_REGENERATE_SCENES
- FORCE_REGENERATE_VIDEO

## Development rule
Before changing anything:
- inspect only relevant files
- make one small change
- do not rewrite the whole project