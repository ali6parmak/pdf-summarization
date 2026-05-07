from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent
DATA_PATH = ROOT_PATH / "data"
PDFS_PATH = DATA_PATH / "pdfs"
SEGMENTATION_PATH = DATA_PATH / "segmentation"

BLUE = "\033[94m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

if __name__ == "__main__":

    ROOT_PATH.mkdir(parents=True, exist_ok=True)
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    PDFS_PATH.mkdir(parents=True, exist_ok=True)
    SEGMENTATION_PATH.mkdir(parents=True, exist_ok=True)

    print(ROOT_PATH)
    print(DATA_PATH)
    print(PDFS_PATH)
    print(SEGMENTATION_PATH)
