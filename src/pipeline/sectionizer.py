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
    return [s for s in segments if s.type in SUMMARIZABLE_TYPES and s.text.strip()]


def get_full_text(segments: list[SegmentBox]) -> str:
    return "\n\n".join(s.text.strip() for s in segments if s.text.strip())


def build_sections(segments: list[SegmentBox]) -> list[Section]:
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
    real = [s for s in sections if s.heading and s.body]
    return len(real) >= 2
