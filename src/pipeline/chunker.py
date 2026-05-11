import re
from configuration import MAX_INPUT_TOKENS
from domain.Section import Section
from pipeline.tokens import estimate_tokens


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
PARAGRAPH_SEPARATOR = "\n\n"
PARAGRAPH_SEPARATOR_TOKENS = estimate_tokens(PARAGRAPH_SEPARATOR)


def pack_sections_into_chunks(
    sections: list[Section],
    budget_tokens: int = MAX_INPUT_TOKENS,
) -> list[str]:
    """Greedily pack rendered sections into chunks that fit `budget_tokens`.

    Sections that are themselves larger than the budget are flushed first,
    then split internally via paragraph- and sentence-based fallbacks.
    """
    rendered_sections = [s.render() for s in sections if s.render()]
    return _pack_pieces(rendered_sections, budget_tokens)


def split_text_into_chunks(text: str, budget_tokens: int = MAX_INPUT_TOKENS) -> list[str]:
    """Split a long block of text into chunks that fit `budget_tokens`.

    The split prefers paragraph boundaries first, then sentence boundaries,
    and finally falls back to fixed-size character windows for pathological
    inputs (e.g. a single token-rich paragraph longer than the budget).
    """
    paragraphs = [p.strip() for p in text.split(PARAGRAPH_SEPARATOR) if p.strip()]
    return _pack_pieces(paragraphs, budget_tokens)


def _pack_pieces(pieces: list[str], budget_tokens: int) -> list[str]:
    """Pack `pieces` (sections or paragraphs) into chunks of `\\n\\n`-joined text.

    Pieces larger than the budget are decomposed into sentence-level chunks.
    Separator tokens between pieces are accounted for so chunks never exceed
    the budget after joining.
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal buffer, buffer_tokens
        if buffer:
            chunks.append(PARAGRAPH_SEPARATOR.join(buffer))
            buffer = []
            buffer_tokens = 0

    for piece in pieces:
        piece_tokens = estimate_tokens(piece)
        if piece_tokens == 0:
            continue

        if piece_tokens > budget_tokens:
            flush()
            chunks.extend(_split_paragraph(piece, budget_tokens))
            continue

        added = piece_tokens + (PARAGRAPH_SEPARATOR_TOKENS if buffer else 0)
        if buffer and buffer_tokens + added > budget_tokens:
            flush()
            buffer.append(piece)
            buffer_tokens = piece_tokens
        else:
            buffer.append(piece)
            buffer_tokens += added

    flush()
    return chunks


def _split_paragraph(paragraph: str, budget_tokens: int) -> list[str]:
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal buffer, buffer_tokens
        if buffer:
            chunks.append(" ".join(buffer))
            buffer = []
            buffer_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if sentence_tokens > budget_tokens:
            flush()
            chunks.extend(_split_by_chars(sentence, budget_tokens))
            continue
        if buffer_tokens + sentence_tokens > budget_tokens:
            flush()
        buffer.append(sentence)
        buffer_tokens += sentence_tokens

    flush()
    return chunks


def _split_by_chars(text: str, budget_tokens: int) -> list[str]:
    char_budget = max(1, budget_tokens * 4)
    return [text[i : i + char_budget] for i in range(0, len(text), char_budget)]


def batch_summaries(
    summaries: list[str],
    budget_tokens: int = MAX_INPUT_TOKENS,
    separator: str = "\n\n---\n\n",
) -> list[list[str]]:
    """Pack a list of summary strings into batches that each fit the budget."""
    separator_tokens = estimate_tokens(separator)
    batches: list[list[str]] = []
    buffer: list[str] = []
    buffer_tokens = 0

    for summary in summaries:
        summary_tokens = estimate_tokens(summary)
        added_tokens = summary_tokens + (separator_tokens if buffer else 0)
        if buffer and buffer_tokens + added_tokens > budget_tokens:
            batches.append(buffer)
            buffer = []
            buffer_tokens = 0
            added_tokens = summary_tokens

        buffer.append(summary)
        buffer_tokens += added_tokens

    if buffer:
        batches.append(buffer)

    # Safety: if everything ended up in a single batch but the recursive
    # reducer asked us to shrink, force a split so we make progress.
    if len(batches) == 1 and len(summaries) > 1:
        mid = len(summaries) // 2
        return [summaries[:mid], summaries[mid:]]
    return batches
