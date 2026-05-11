import json
import subprocess
from configuration import PDFS_PATH, SEGMENTATION_PATH, BLUE, YELLOW, GREEN, RESET


def analyze_documents():
    for file_path in PDFS_PATH.iterdir():
        segmentation_path = SEGMENTATION_PATH / file_path.name.replace(".pdf", ".json")
        if segmentation_path.exists():
            continue

        print(f"{BLUE}Analyzing:{RESET} {YELLOW}{file_path.name}{RESET}")

        command = [
            "curl",
            "-X",
            "POST",
            "-F",
            f"file=@{file_path.as_posix()}",
            "localhost:5060",
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        segmentation_data = json.loads(result.stdout)
        segmentation_path.write_text(json.dumps(segmentation_data, indent=4))
    print(f"{GREEN}All documents analyzed{RESET}")


if __name__ == "__main__":
    analyze_documents()
