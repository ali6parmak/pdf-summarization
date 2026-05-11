from configuration import BLUE, GRAY, GREEN, MAX_INPUT_TOKENS, RESET, YELLOW
from domain.SegmentBox import SegmentBox
from pipeline.chunker import (
    batch_summaries,
    pack_sections_into_chunks,
    split_text_into_chunks,
)
from pipeline.ollama_client import ask_llm
from pipeline.prompts import (
    CHUNK_TEMPLATE,
    REDUCE_FINAL_TEMPLATE,
    REDUCE_INTERMEDIATE_TEMPLATE,
    SINGLE_PASS_TEMPLATE,
    SYSTEM_PROMPT,
)
from pipeline.sectionizer import (
    build_sections,
    filter_segments,
    get_full_text,
    has_useful_structure,
)
from pipeline.tokens import estimate_tokens

REDUCE_SEPARATOR = "\n\n---\n\n"
MAX_REDUCE_DEPTH = 6


def summarize_segments(segments: list[SegmentBox]) -> str:
    useful_segments = filter_segments(segments)
    if not useful_segments:
        return ""

    full_text = get_full_text(useful_segments)
    total_tokens = estimate_tokens(full_text)
    final_word_target = _final_word_target(total_tokens)

    print(f"{BLUE}Useful tokens (estimated):{RESET} {total_tokens}")
    print(f"{BLUE}Per-call input budget:{RESET} {MAX_INPUT_TOKENS}")
    print(f"{BLUE}Final word target:{RESET} {final_word_target}")

    if total_tokens <= MAX_INPUT_TOKENS:
        print(f"{BLUE}Strategy:{RESET} single-pass")
        return _single_pass(full_text, final_word_target)

    sections = build_sections(useful_segments)
    if has_useful_structure(sections):
        chunks = pack_sections_into_chunks(sections, MAX_INPUT_TOKENS)
        print(f"{BLUE}Strategy:{RESET} section-based map-reduce ({len(sections)} sections, {len(chunks)} chunks)")
    else:
        chunks = split_text_into_chunks(full_text, MAX_INPUT_TOKENS)
        print(f"{BLUE}Strategy:{RESET} text-based map-reduce ({len(chunks)} chunks)")

    partial_summaries = _summarize_chunks(chunks)
    return _recursive_reduce(partial_summaries, final_word_target)


def _final_word_target(input_tokens: int) -> str:
    if input_tokens <= 2000:
        return "150-300"
    if input_tokens <= 8000:
        return "300-450"
    return "400-500"


def _intermediate_word_target(content_tokens: int) -> int:
    return max(120, min(400, content_tokens // 8))


def _single_pass(content: str, word_target: str) -> str:
    prompt = SINGLE_PASS_TEMPLATE.format(content=content, word_target=word_target)
    return ask_llm(prompt, system=SYSTEM_PROMPT)


def _summarize_chunks(chunks: list[str]) -> list[str]:
    summaries: list[str] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        chunk_tokens = estimate_tokens(chunk)
        word_target = _intermediate_word_target(chunk_tokens)
        prompt = CHUNK_TEMPLATE.format(
            part_index=index,
            part_count=total,
            content=chunk,
            word_target=word_target,
        )
        print(
            f"{YELLOW}Summarizing chunk {index}/{total}{RESET} "
            f"{GRAY}(~{chunk_tokens} tok input -> ~{word_target} words){RESET}"
        )
        summaries.append(ask_llm(prompt, system=SYSTEM_PROMPT))
    return summaries


def _recursive_reduce(summaries: list[str], final_word_target: str, depth: int = 0) -> str:
    if not summaries:
        return ""

    joined = REDUCE_SEPARATOR.join(summaries)
    joined_tokens = estimate_tokens(joined)

    if joined_tokens <= MAX_INPUT_TOKENS:
        print(f"{GREEN}Final reduce of {len(summaries)} partial summaries " f"(~{joined_tokens} tok, depth {depth}){RESET}")
        return _reduce_final(joined, final_word_target)

    if depth >= MAX_REDUCE_DEPTH:
        # Hard safety cap: truncate the joined input to the budget and run
        # the final reducer. In practice each reduce shrinks ~10x, so even
        # very long documents converge in 2-3 levels and we never reach this.
        print(f"{YELLOW}Reduce depth cap reached ({MAX_REDUCE_DEPTH}), " f"truncating to budget and finalizing.{RESET}")
        truncated = joined[: MAX_INPUT_TOKENS * 4]
        return _reduce_final(truncated, final_word_target)

    batches = batch_summaries(summaries, MAX_INPUT_TOKENS, REDUCE_SEPARATOR)
    print(f"{YELLOW}Intermediate reduce: {len(summaries)} summaries " f"-> {len(batches)} batches (depth {depth}){RESET}")

    next_level: list[str] = []
    for index, batch in enumerate(batches, start=1):
        content = REDUCE_SEPARATOR.join(batch)
        word_target = _intermediate_word_target(estimate_tokens(content))
        prompt = REDUCE_INTERMEDIATE_TEMPLATE.format(content=content, word_target=word_target)
        print(f"{YELLOW}Reducing batch {index}/{len(batches)} " f"({len(batch)} summaries -> ~{word_target} words){RESET}")
        next_level.append(ask_llm(prompt, system=SYSTEM_PROMPT))

    return _recursive_reduce(next_level, final_word_target, depth + 1)


def _reduce_final(content: str, word_target: str) -> str:
    prompt = REDUCE_FINAL_TEMPLATE.format(content=content, word_target=word_target)
    return ask_llm(prompt, system=SYSTEM_PROMPT)
