import json
from pathlib import Path

from configuration import BLUE, GREEN, RED, YELLOW, RESET, SEGMENTATION_PATH, SUMMARIES_PATH
from domain.SegmentBox import SegmentBox
from pipeline.strategies import resolve_strategy


def load_segments(json_path: Path) -> list[SegmentBox]:
    raw = json.loads(json_path.read_text())
    return [SegmentBox(**item) for item in raw]


def summarize(strategy: str = "recursive_reduce", top_percent: float = 50.0, overwrite: bool = False) -> None:
    summarizer = resolve_strategy(strategy, top_percent=top_percent)
    output_dir = SUMMARIES_PATH / strategy
    output_dir.mkdir(parents=True, exist_ok=True)

    for segmentation_file_path in SEGMENTATION_PATH.glob("*.json"):
        summary_output_path = output_dir / segmentation_file_path.name.replace(".json", ".txt")
        if summary_output_path.exists() and not overwrite:
            print(f"{YELLOW}Skipping (already summarized):{RESET} {segmentation_file_path.name}")
            continue

        print(f"\n{BLUE}=== Summarizing [{strategy}]:{RESET} {segmentation_file_path.name}")
        try:
            segments = load_segments(segmentation_file_path)
            summary = summarizer(segments)
        except Exception as e:
            print(f"{RED}Failed to summarize {segmentation_file_path.name}: {e}{RESET}")
            continue

        if not summary.strip():
            print(f"{YELLOW}Empty summary produced for {segmentation_file_path.name}, skipping save.{RESET}")
            continue

        summary_output_path.write_text(summary.rstrip() + "\n")
        print(f"{GREEN}Saved summary -> {summary_output_path}{RESET}")


if __name__ == "__main__":
    summarize(strategy="recursive_reduce", top_percent=50.0, overwrite=False)
