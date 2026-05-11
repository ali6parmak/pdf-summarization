import json
from pathlib import Path

from configuration import (
    BLUE,
    GREEN,
    RED,
    RESET,
    SEGMENTATION_PATH,
    SUMMARIES_PATH,
    YELLOW,
)
from domain.SegmentBox import SegmentBox
from pipeline.summarizer import summarize_segments


def load_segments(json_path: Path) -> list[SegmentBox]:
    raw = json.loads(json_path.read_text())
    return [SegmentBox(**item) for item in raw]


def summarize_all(overwrite: bool = False) -> None:
    SUMMARIES_PATH.mkdir(parents=True, exist_ok=True)
    for segmentation_file_path in SEGMENTATION_PATH.glob("*.json"):
        summary_output_path = SUMMARIES_PATH / segmentation_file_path.name.replace(".json", ".txt")
        if summary_output_path.exists() and not overwrite:
            print(f"{YELLOW}Skipping (already summarized):{RESET} {segmentation_file_path.name}")
            continue

        print(f"\n{BLUE}=== Summarizing:{RESET} {segmentation_file_path.name}")
        try:
            segments = load_segments(segmentation_file_path)
            summary = summarize_segments(segments)
        except Exception as e:
            print(f"{RED}Failed to summarize {segmentation_file_path.name}: {e}{RESET}")
            continue

        if not summary.strip():
            print(f"{YELLOW}Empty summary produced for {segmentation_file_path.name}, skipping save.{RESET}")
            continue

        summary_output_path.write_text(summary.rstrip() + "\n")
        print(f"{GREEN}Saved summary -> {summary_output_path}{RESET}")


if __name__ == "__main__":
    summarize_all()
