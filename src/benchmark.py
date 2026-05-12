import json
import time
from datetime import datetime, timezone
from pathlib import Path

from configuration import (
    BLUE,
    GREEN,
    LLM_MODEL,
    RED,
    RESET,
    SEGMENTATION_PATH,
    SUMMARIES_PATH,
    YELLOW,
)
from domain.SegmentBox import SegmentBox
from pipeline.sectionizer import filter_segments, get_full_text
from pipeline.summarizer import summarize_segments
from pipeline.tokens import estimate_tokens
from summarize import load_segments

BENCHMARK_FILENAME = "summarization_benchmark.md"


def _quick_segment_count(json_path: Path) -> int:
    return len(json.loads(json_path.read_text()))


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _pearson_r(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return cov / (var_x**0.5 * var_y**0.5)


def _write_benchmark_markdown(
    path: Path,
    rows: list[dict],
    run_t0: float,
    run_t1: float,
) -> None:
    lines: list[str] = [
        "# Summarization benchmark",
        "",
        f"- **Run finished (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z",
        f"- **Wall time (full run):** {run_t1 - run_t0:.3f}s",
        f"- **Model:** `{LLM_MODEL}`",
        "",
        "| Source file | Segments | Useful segments | Est. input tokens | Time (s) | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        seg = row["segments"]
        useg = row["useful_segments"]
        toks = row["est_tokens"]
        t = row["time_s"]
        time_cell = f"{t:.3f}" if isinstance(t, (int, float)) else str(t)
        seg_cell = str(seg) if seg != "—" else "—"
        useg_cell = str(useg) if useg != "—" else "—"
        tok_cell = str(toks) if toks != "—" else "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_md_cell(str(row["source_file"])),
                    seg_cell,
                    useg_cell,
                    tok_cell,
                    time_cell,
                    _escape_md_cell(str(row["status"])),
                ]
            )
            + " |"
        )

    completed_times = [r["time_s"] for r in rows if r["status"] == "Completed" and isinstance(r["time_s"], (int, float))]
    completed_with_metrics = [
        r
        for r in rows
        if r["status"] == "Completed" and isinstance(r["est_tokens"], int) and isinstance(r["time_s"], (int, float))
    ]
    lines.extend(
        [
            "",
            "## Totals",
            "",
            f"- **Files in run:** {len(rows)}",
            f"- **Completed:** {sum(1 for r in rows if r['status'] == 'Completed')}",
            f"- **Skipped:** {sum(1 for r in rows if r['status'] == 'Skipped')}",
            f"- **Failed / empty:** {sum(1 for r in rows if r['status'] == 'Empty' or str(r['status']).startswith('Failed:'))}",
        ]
    )
    if completed_times:
        lines.append(f"- **Summarization time (completed only):** {sum(completed_times):.3f}s")

    if completed_with_metrics:
        total_est_tokens = sum(int(r["est_tokens"]) for r in completed_with_metrics)
        total_time_s = sum(float(r["time_s"]) for r in completed_with_metrics)
        lines.append(f"- **Total est. input tokens (completed):** {total_est_tokens}")
        if total_est_tokens > 0 and total_time_s > 0:
            est_tok_per_s = total_est_tokens / total_time_s
            s_per_1k_tok = 1000.0 * total_time_s / total_est_tokens
            lines.append(
                f"- **Est. throughput (completed, Σ tokens ÷ Σ time):** {est_tok_per_s:.1f} est. tok/s "
                f"({s_per_1k_tok:.3f}s per 1k est. tokens)"
            )
        tok_vals = [float(r["est_tokens"]) for r in completed_with_metrics]
        time_vals = [float(r["time_s"]) for r in completed_with_metrics]
        r_tokens_time = _pearson_r(tok_vals, time_vals)
        if r_tokens_time is not None:
            lines.append(
                f"- **Pearson r (est. tokens vs. time, completed):** {r_tokens_time:.3f} "
                f"(1 ≈ larger inputs take longer; n={len(completed_with_metrics)})"
            )
        elif len(completed_with_metrics) >= 2:
            lines.append(
                "- **Pearson r (est. tokens vs. time, completed):** n/a "
                "(no variation in est. tokens or in time across completed files)"
            )
        elif len(completed_with_metrics) == 1:
            lines.append("- **Pearson r (est. tokens vs. time, completed):** n/a (only one completed file with metrics)")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def benchmark(overwrite: bool = False) -> None:
    SUMMARIES_PATH.mkdir(parents=True, exist_ok=True)
    benchmark_rows: list[dict] = []
    run_t0 = time.perf_counter()

    for segmentation_file_path in sorted(SEGMENTATION_PATH.glob("*.json")):
        summary_output_path = SUMMARIES_PATH / segmentation_file_path.name.replace(".json", ".txt")
        if summary_output_path.exists() and not overwrite:
            print(f"{YELLOW}Skipping (already summarized):{RESET} {segmentation_file_path.name}")
            try:
                seg_n = _quick_segment_count(segmentation_file_path)
            except Exception:
                seg_n = "—"
            benchmark_rows.append(
                {
                    "source_file": segmentation_file_path.name,
                    "segments": seg_n,
                    "useful_segments": "—",
                    "est_tokens": "—",
                    "time_s": "—",
                    "status": "Skipped",
                }
            )
            continue

        print(f"\n{BLUE}=== Summarizing:{RESET} {segmentation_file_path.name}")
        t0 = time.perf_counter()
        segments: list[SegmentBox] = []
        segment_count: int | str = "—"
        useful_count: int | str = "—"
        est_tokens: int | str = "—"

        try:
            segments = load_segments(segmentation_file_path)
            segment_count = len(segments)
            useful = filter_segments(segments)
            useful_count = len(useful)
            full_text = get_full_text(useful)
            est_tokens = estimate_tokens(full_text) if useful else 0

            summary = summarize_segments(segments)
            elapsed = time.perf_counter() - t0

            if not summary.strip():
                print(f"{YELLOW}Empty summary produced for {segmentation_file_path.name}, skipping save.{RESET}")
                benchmark_rows.append(
                    {
                        "source_file": segmentation_file_path.name,
                        "segments": segment_count,
                        "useful_segments": useful_count,
                        "est_tokens": est_tokens,
                        "time_s": elapsed,
                        "status": "Empty",
                    }
                )
                continue

            summary_output_path.write_text(summary.rstrip() + "\n")
            print(f"{GREEN}Saved summary -> {summary_output_path}{RESET}")
            benchmark_rows.append(
                {
                    "source_file": segmentation_file_path.name,
                    "segments": segment_count,
                    "useful_segments": useful_count,
                    "est_tokens": est_tokens,
                    "time_s": elapsed,
                    "status": "Completed",
                }
            )
        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f"{RED}Failed to summarize {segmentation_file_path.name}: {e}{RESET}")
            err_short = _escape_md_cell(str(e))
            if len(err_short) > 120:
                err_short = err_short[:117] + "..."
            benchmark_rows.append(
                {
                    "source_file": segmentation_file_path.name,
                    "segments": segment_count,
                    "useful_segments": useful_count if segments else "—",
                    "est_tokens": est_tokens if segments else "—",
                    "time_s": elapsed,
                    "status": f"Failed: {err_short}",
                }
            )

    run_t1 = time.perf_counter()
    benchmark_path = SUMMARIES_PATH / BENCHMARK_FILENAME
    _write_benchmark_markdown(benchmark_path, benchmark_rows, run_t0, run_t1)
    print(f"\n{GREEN}Wrote benchmark -> {benchmark_path}{RESET}")


if __name__ == "__main__":
    benchmark()
