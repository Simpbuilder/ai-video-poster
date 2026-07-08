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

for topic in read_topics("topics.txt"):
    folder_path = create_topic_folder(topic)

    try:
        script = generate_script(topic)
    except ScriptGenerationError as error:
        print(f"Could not generate a script for '{topic}': {error}")
        continue

    script_path = save_script(folder_path, script)
    save_metadata(folder_path, topic, MODEL_NAME)
    print(f"Saved script: {script_path}")
