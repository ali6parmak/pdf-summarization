import re

from pdf_token_type_labels import TokenType

from domain.SegmentBox import SegmentBox
from domain.Section import Section
from pipeline.sectionizer import HEADING_TYPES
from pipeline.tokens import estimate_tokens

_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_TOPIC_MAX_CHARS = 240


def build_heading_skeleton(segments: list[SegmentBox]) -> str:
    lines: list[str] = []
    for seg in segments:
        if seg.type not in HEADING_TYPES:
            continue
        text = seg.text.strip()
        if not text:
            continue
        prefix = "# " if seg.type == TokenType.TITLE else "## "
        lines.append(prefix + text)
    return "\n".join(lines)


def build_section_topics(sections: list[Section]) -> str:
    lines: list[str] = []
    for section in sections:
        if not section.heading:
            continue
        topic = _first_sentence(section.body)
        if topic:
            lines.append(f"- {section.heading}: {topic}")
        else:
            lines.append(f"- {section.heading}: (no body text)")
    return "\n".join(lines)


def select_boundary_anchors(
    segments: list[SegmentBox],
    budget_tokens: int,
) -> tuple[str, str]:
    if budget_tokens <= 0 or not segments:
        return "", ""

    half = max(1, budget_tokens // 2)

    head_parts: list[str] = []
    head_tokens = 0
    head_end_idx = 0
    for i, seg in enumerate(segments):
        text = seg.text.strip()
        if not text:
            continue
        t = estimate_tokens(text)
        if head_parts and head_tokens + t > half:
            break
        head_parts.append(text)
        head_tokens += t
        head_end_idx = i + 1

    tail_parts: list[str] = []
    tail_tokens = 0
    for i in range(len(segments) - 1, head_end_idx - 1, -1):
        seg = segments[i]
        text = seg.text.strip()
        if not text:
            continue
        t = estimate_tokens(text)
        if tail_parts and tail_tokens + t > half:
            break
        tail_parts.append(text)
        tail_tokens += t

    tail_parts.reverse()
    return "\n\n".join(head_parts), "\n\n".join(tail_parts)


def select_top_by_length(
    segments: list[SegmentBox],
    top_percent: float,
) -> list[SegmentBox]:

    if not segments:
        return []
    pct = max(0.0, min(100.0, top_percent))
    if pct >= 100.0:
        return list(segments)
    if pct <= 0.0:
        return []

    keep_n = max(1, int(round(len(segments) * pct / 100.0)))
    indexed = list(enumerate(segments))
    indexed.sort(key=lambda pair: len(pair[1].text.strip()), reverse=True)
    chosen = sorted(indexed[:keep_n], key=lambda pair: pair[0])
    return [seg for _, seg in chosen]


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    parts = _SENTENCE_END_RE.split(text, maxsplit=1)
    first = parts[0].strip()
    if len(first) > _TOPIC_MAX_CHARS:
        return first[: _TOPIC_MAX_CHARS - 1].rstrip() + "…"
    return first
