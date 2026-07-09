from config import (
    COPY_SCRIPT_TO_APPROVAL,
    MAX_TOPICS,
    OPENAI_MODEL,
    SKIP_EXISTING_SCRIPTS,
)
from generators.script_generator import ScriptGenerationError, generate_script
from utils.file_utils import (
    copy_script_to_approval,
    create_topic_folder,
    read_topics,
    save_metadata,
    save_script,
)
from utils.cost_tracker import log_usage
from utils.logger import log

log("Program started.")

topics = list(read_topics("topics.txt"))

if MAX_TOPICS is not None:
    topics = topics[:MAX_TOPICS]

log(f"Topics to process: {len(topics)}")

for topic in topics:
    log(f"Processing topic: {topic}")
    folder_path = create_topic_folder(topic)
    existing_script = folder_path / "script.txt"

    if SKIP_EXISTING_SCRIPTS and existing_script.exists():
        log(f"Skipping topic because script already exists: {topic}")
        continue

    try:
        script, usage = generate_script(topic)
    except ScriptGenerationError as error:
        log(f"Could not generate a script for '{topic}': {error}")
        continue

    log_usage(topic, OPENAI_MODEL, usage)

    script_path = save_script(folder_path, script)
    log(f"Saved script: {script_path}")

    metadata_path = save_metadata(folder_path, topic, OPENAI_MODEL, usage)
    log(f"Saved metadata: {metadata_path}")

    if COPY_SCRIPT_TO_APPROVAL:
        approval_script_path = copy_script_to_approval(topic, script_path)
        log(f"Copied script to approval: {approval_script_path}")

log("Program finished.")
