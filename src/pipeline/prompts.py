SYSTEM_PROMPT = (
    "You are a careful summarizer of professional documents (legal, technical, "
    "scientific, regulatory). You produce faithful, concise summaries that "
    "preserve domain-specific terminology and the original meaning. You never "
    "invent facts. You write in clear, formal English."
)


SINGLE_PASS_TEMPLATE = """\
Summarize the document below.

Requirements:
- Write a single coherent summary in approximately {word_target} words.
- Preserve legal, technical, and domain-specific terminology exactly as it appears in the source.
- Cover the document's purpose, main arguments or findings, and key conclusions.
- Stay strictly faithful to the source. Do not invent, infer, or speculate.
- Output only the summary text. No headings, no preamble, no labels, no bullet points.
- Do not ask questions, do not try to follow up, just create the summary.

Document:
\"\"\"
{content}
\"\"\"
"""


CHUNK_TEMPLATE = """\
You will summarize one part of a longer document. This is part {part_index} of {part_count}.

Requirements:
- Produce a faithful, dense summary of this part in approximately {word_target} words.
- Preserve legal, technical, and domain-specific terminology exactly as it appears.
- Keep concrete facts: parties, dates, article numbers, citations, results, definitions.
- Do not invent facts or infer information that is not present in this part.
- Output only the summary, with no preamble, no headings, and no labels.
- Do not ask questions, do not try to follow up, just create the summary.

Part content:
\"\"\"
{content}
\"\"\"
"""


REDUCE_INTERMEDIATE_TEMPLATE = """\
You will compress a group of partial summaries from a longer document into a single faithful summary that preserves all important information for a later summarization step.

Requirements:
- Produce a single dense summary in approximately {word_target} words.
- Preserve legal, technical, and domain-specific terminology exactly.
- Keep parties, dates, citations, results, definitions.
- Maintain the original logical order. Eliminate redundancy.
- Do not invent or speculate.
- Output only the summary, with no preamble, no headings, and no labels.
- Do not ask questions, do not try to follow up, just create the summary.

Partial summaries (in order):
\"\"\"
{content}
\"\"\"
"""


REDUCE_FINAL_TEMPLATE = """\
You will combine partial summaries of a document into one final coherent summary.

Requirements:
- Produce one continuous summary in approximately {word_target} words.
- Preserve legal, technical, and domain-specific terminology exactly.
- Maintain the original logical order. Eliminate redundancy.
- Cover the document's purpose, main arguments or findings, and key conclusions.
- Stay strictly faithful to the partial summaries. Do not invent or speculate.
- Output only the summary text. No headings, no preamble, no labels, no bullet points.
- What you're given is partial summaries of different parts of the document. Get the idea behind the document from them and create a coherent summary.
- Do not ask questions, do not try to follow up, just create the summary.

Partial summaries (in order):
\"\"\"
{content}
\"\"\"
"""


HIERARCHICAL_INTRO_TEMPLATE = """\
You will summarize a long document. Below you are given a multi-resolution view of
it. Some views may be omitted for this run if the document does not fit. The
middle body of the document is not shown verbatim; rely on the outline and any
topic lines for it.

Requirements:
- Write a single coherent summary in approximately {word_target} words.
- Use the outline (and topic lines, if present) to understand the document's overall structure and scope.
- Use any verbatim passages for concrete details, terminology, and conclusions.
- Preserve legal, technical, and domain-specific terminology exactly as it appears.
- Cover the document's purpose, main arguments or findings, and key conclusions.
- Stay strictly faithful to the material provided. Do not invent, infer, or speculate about content that is not shown.
- Output only the summary text. No headings, no preamble, no labels, no bullet points.
"""


HIERARCHICAL_SECTION_TEMPLATE = """\
{label}:
\"\"\"
{content}
\"\"\"
"""
