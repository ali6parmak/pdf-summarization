from configuration import CHARS_PER_TOKEN


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in `text` using a chars-per-token ratio.

    The exact ratio depends on the tokenizer, but ~4 characters per token is a
    good heuristic for English text and frees us from having to ship a
    tokenizer dependency that matches the chosen Ollama model.
    """
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN
