from config import MAX_TOPICS, OPENAI_MODEL
from generators.script_generator import ScriptGenerationError, generate_script
from utils.file_utils import (
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

log("Program finished.")
