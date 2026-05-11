from pdf_token_type_labels import TokenType

from domain.SegmentBox import SegmentBox
from domain.Section import Section


SUMMARIZABLE_TYPES = {
    TokenType.TITLE,
    TokenType.SECTION_HEADER,
    TokenType.TEXT,
    TokenType.LIST_ITEM,
}
HEADING_TYPES = {TokenType.TITLE, TokenType.SECTION_HEADER}
BODY_TYPES = {TokenType.TEXT, TokenType.LIST_ITEM}


def filter_segments(segments: list[SegmentBox]) -> list[SegmentBox]:
    """Keep only the segment types that carry summarizable content."""
    return [s for s in segments if s.type in SUMMARIZABLE_TYPES and s.text.strip()]


def get_full_text(segments: list[SegmentBox]) -> str:
    """Join all useful segments into one document string in reading order."""
    return "\n\n".join(s.text.strip() for s in segments if s.text.strip())


def build_sections(segments: list[SegmentBox]) -> list[Section]:
    """Group consecutive Text/list-item segments under their preceding heading.

    The input is assumed to already be in reading order (which is how the
    upstream segmentation pipeline emits the JSON).
    """
    sections: list[Section] = []
    heading = ""
    level = 0
    body_parts: list[str] = []

    def flush() -> None:
        nonlocal heading, level, body_parts
        if heading or body_parts:
            sections.append(
                Section(
                    heading=heading,
                    body="\n\n".join(body_parts).strip(),
                    level=level,
                )
            )
        heading = ""
        level = 0
        body_parts = []

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        if seg.type in HEADING_TYPES:
            flush()
            heading = text
            level = 1 if seg.type == TokenType.TITLE else 2
        elif seg.type in BODY_TYPES:
            body_parts.append(text)

    flush()
    return [s for s in sections if s.is_useful]


def has_useful_structure(sections: list[Section]) -> bool:
    """Return True if the section list looks like a real navigable structure.

    A "real" section needs both a heading and some body, and we want at least
    two of those before we consider section-based summarization worthwhile.
    """
    real = [s for s in sections if s.heading and s.body]
    return len(real) >= 2
