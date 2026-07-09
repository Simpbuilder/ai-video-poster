from pathlib import Path


def split_into_chunks(script, words_per_chunk=8):
    words = script.split()
    chunks = []

    for position in range(0, len(words), words_per_chunk):
        chunk_words = words[position:position + words_per_chunk]
        chunks.append(" ".join(chunk_words))

    return chunks


def format_srt_time(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},000"


def generate_subtitles(script, output_path):
    chunks = split_into_chunks(script)
    subtitle_lines = []

    for number, chunk in enumerate(chunks, start=1):
        start_time = (number - 1) * 3
        end_time = number * 3

        subtitle_lines.append(str(number))
        subtitle_lines.append(
            f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}"
        )
        subtitle_lines.append(chunk)
        subtitle_lines.append("")

    Path(output_path).write_text(
        "\n".join(subtitle_lines),
        encoding="utf-8",
    )
