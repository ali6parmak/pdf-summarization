from typing import Callable

from configuration import BLUE, MAX_INPUT_TOKENS, RESET, YELLOW
from domain.SegmentBox import SegmentBox
from pipeline.extract import (
    build_heading_skeleton,
    build_section_topics,
    select_boundary_anchors,
    select_top_by_length,
)
from pipeline.ollama_client import ask_llm
from pipeline.prompts import (
    HIERARCHICAL_INTRO_TEMPLATE,
    HIERARCHICAL_SECTION_TEMPLATE,
    SYSTEM_PROMPT,
)
from pipeline.sectionizer import (
    build_sections,
    filter_segments,
    get_full_text,
    has_useful_structure,
)
from pipeline.summarizer import final_word_target, single_pass, summarize_segments
from pipeline.tokens import estimate_tokens

# Slack reserved inside MAX_INPUT_TOKENS for the hierarchical prompt's
# scaffolding (intro paragraph, section labels, quote markers).
_HIERARCHICAL_PROMPT_OVERHEAD = 250

# When the topics list would crush the verbatim-anchor budget below this
# fraction of MAX_INPUT_TOKENS, we drop topics and use the freed budget for
# verbatim anchors instead. The structural skeleton is always kept if it fits.
_MIN_ANCHOR_FRACTION = 0.30

StrategyFn = Callable[[list[SegmentBox]], str]


def summarize_hierarchical(segments: list[SegmentBox]) -> str:
    useful = filter_segments(segments)
    if not useful:
        return ""

    full_text = get_full_text(useful)
    total_tokens = estimate_tokens(full_text)
    word_target = final_word_target(total_tokens)

    print(f"{BLUE}Useful tokens (estimated):{RESET} {total_tokens}")
    print(f"{BLUE}Per-call input budget:{RESET} {MAX_INPUT_TOKENS}")
    print(f"{BLUE}Final word target:{RESET} {word_target}")

    if total_tokens <= MAX_INPUT_TOKENS:
        print(f"{BLUE}Strategy:{RESET} hierarchical -> single-pass (already fits)")
        return single_pass(full_text, word_target)

    sections = build_sections(useful)
    if not has_useful_structure(sections):
        print(f"{YELLOW}Hierarchical: no useful section structure; falling back to recursive_reduce.{RESET}")
        return summarize_segments(segments)

    skeleton = build_heading_skeleton(useful)
    topics = build_section_topics(sections)
    skel_tok = estimate_tokens(skeleton)
    topics_tok = estimate_tokens(topics)

    body_budget = MAX_INPUT_TOKENS - _HIERARCHICAL_PROMPT_OVERHEAD
    min_anchor = int(body_budget * _MIN_ANCHOR_FRACTION)

    if skel_tok + min_anchor > body_budget:
        print(
            f"{YELLOW}Hierarchical: heading skeleton too large for budget "
            f"(~{skel_tok} tok); falling back to recursive_reduce.{RESET}"
        )
        return summarize_segments(segments)

    include_topics = (skel_tok + topics_tok + min_anchor) <= body_budget
    if not include_topics:
        print(
            f"{YELLOW}Hierarchical: dropping per-section topics "
            f"(~{topics_tok} tok) to keep verbatim anchor budget.{RESET}"
        )
        topics = ""
        topics_tok = 0

    anchor_budget = body_budget - skel_tok - topics_tok
    head, tail = select_boundary_anchors(useful, anchor_budget)
    head_tok = estimate_tokens(head)
    tail_tok = estimate_tokens(tail)

    print(
        f"{BLUE}Strategy:{RESET} hierarchical "
        f"(skeleton ~{skel_tok} tok"
        + (f", topics ~{topics_tok} tok" if include_topics else ", topics omitted")
        + f", head ~{head_tok} tok, tail ~{tail_tok} tok)"
    )

    prompt = _build_hierarchical_prompt(
        skeleton=skeleton,
        topics=topics if include_topics else "",
        head=head,
        tail=tail,
        word_target=word_target,
    )
    return ask_llm(prompt, system=SYSTEM_PROMPT)


def _build_hierarchical_prompt(
    skeleton: str,
    topics: str,
    head: str,
    tail: str,
    word_target: str,
) -> str:
    parts: list[str] = [HIERARCHICAL_INTRO_TEMPLATE.format(word_target=word_target).rstrip()]
    if skeleton.strip():
        parts.append(
            HIERARCHICAL_SECTION_TEMPLATE.format(label="Document outline (headings in order)", content=skeleton).rstrip()
        )
    if topics.strip():
        parts.append(
            HIERARCHICAL_SECTION_TEMPLATE.format(
                label="Per-section topics (one line per section, in order)",
                content=topics,
            ).rstrip()
        )
    if head.strip():
        parts.append(HIERARCHICAL_SECTION_TEMPLATE.format(label="Verbatim opening passages", content=head).rstrip())
    if tail.strip():
        parts.append(HIERARCHICAL_SECTION_TEMPLATE.format(label="Verbatim closing passages", content=tail).rstrip())
    return "\n\n".join(parts) + "\n"


def summarize_length_sample(
    segments: list[SegmentBox],
    top_percent: float = 50.0,
) -> str:
    useful = filter_segments(segments)
    if not useful:
        return ""

    sampled = select_top_by_length(useful, top_percent)
    if not sampled:
        return ""

    sampled_text = get_full_text(sampled)
    sampled_tokens = estimate_tokens(sampled_text)
    original_tokens = estimate_tokens(get_full_text(useful))
    word_target = final_word_target(sampled_tokens)

    print(
        f"{BLUE}Strategy:{RESET} length_sample "
        f"(top {top_percent:.1f}% -> {len(sampled)}/{len(useful)} segments, "
        f"~{sampled_tokens}/{original_tokens} tok)"
    )

    if sampled_tokens <= MAX_INPUT_TOKENS:
        return single_pass(sampled_text, word_target)

    print(f"{YELLOW}length_sample: sample still exceeds budget; routing the sample through recursive_reduce.{RESET}")
    return summarize_segments(sampled)


_STRATEGIES = {
    "recursive_reduce": "recursive_reduce",
    "hierarchical": "hierarchical",
    "length_sample": "length_sample",
}


def available_strategies() -> list[str]:
    return list(_STRATEGIES.keys())


def resolve_strategy(name: str, top_percent: float = 50.0) -> StrategyFn:

    if name == "recursive_reduce":
        return summarize_segments
    if name == "hierarchical":
        return summarize_hierarchical
    if name == "length_sample":
        return lambda segments: summarize_length_sample(segments, top_percent=top_percent)
    raise ValueError(f"Unknown strategy: {name!r}. Available: {available_strategies()}")
