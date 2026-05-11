import os
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent
DATA_PATH = ROOT_PATH / "data"
PDFS_PATH = DATA_PATH / "pdfs"
SEGMENTATION_PATH = DATA_PATH / "segmentation"
SUMMARIES_PATH = DATA_PATH / "summaries"

# LLM configuration. Override either via environment variables or by editing
# the defaults below. The model must be available in your local Ollama install.
LLM_MODEL = os.environ.get("PDF_SUMMARIZER_MODEL", "gemma4:e2b")
LLM_HOST = os.environ.get("PDF_SUMMARIZER_OLLAMA_HOST")  # None -> default ollama URL
LLM_TEMPERATURE = float(os.environ.get("PDF_SUMMARIZER_TEMPERATURE", "0.2"))

# Token-budget configuration. We use a heuristic of CHARS_PER_TOKEN characters
# per token for estimation -- close enough for English text and free of any
# tokenizer dependency. CONTEXT_TOKENS should be set to the model's context
# window; the remaining budget after reserving room for prompt overhead and
# the model's output is what we can fill with source content per call.
CHARS_PER_TOKEN = 4
CONTEXT_TOKENS = int(os.environ.get("PDF_SUMMARIZER_CONTEXT_TOKENS", "8000"))
PROMPT_OVERHEAD_TOKENS = 400
OUTPUT_BUFFER_TOKENS = 800
MAX_INPUT_TOKENS = CONTEXT_TOKENS - PROMPT_OVERHEAD_TOKENS - OUTPUT_BUFFER_TOKENS

BLUE = "\033[94m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"
RESET = "\033[0m"

if __name__ == "__main__":

    ROOT_PATH.mkdir(parents=True, exist_ok=True)
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    PDFS_PATH.mkdir(parents=True, exist_ok=True)
    SEGMENTATION_PATH.mkdir(parents=True, exist_ok=True)
    SUMMARIES_PATH.mkdir(parents=True, exist_ok=True)

    print(ROOT_PATH)
    print(DATA_PATH)
    print(PDFS_PATH)
    print(SEGMENTATION_PATH)
    print(SUMMARIES_PATH)
    print(f"Model: {LLM_MODEL}")
    print(f"Context tokens: {CONTEXT_TOKENS}")
    print(f"Max input tokens per call: {MAX_INPUT_TOKENS}")
