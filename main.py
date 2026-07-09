from generators.script_generator import (
    MODEL_NAME,
    ScriptGenerationError,
    generate_script,
)
from utils.file_utils import (
    create_topic_folder,
    read_topics,
    save_metadata,
    save_script,
)
from utils.logger import log

log("Program started.")

for topic in read_topics("topics.txt"):
    log(f"Processing topic: {topic}")
    folder_path = create_topic_folder(topic)

    try:
        script = generate_script(topic)
    except ScriptGenerationError as error:
        log(f"Could not generate a script for '{topic}': {error}")
        continue

    script_path = save_script(folder_path, script)
    log(f"Saved script: {script_path}")

    metadata_path = save_metadata(folder_path, topic, MODEL_NAME)
    log(f"Saved metadata: {metadata_path}")

log("Program finished.")
