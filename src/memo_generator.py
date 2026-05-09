from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd


PROMPT_PATH = Path("prompts/campaign_memo_prompt.md")
DEFAULT_MODEL_NAME = "gemini-2.5-flash-lite"
REQUEST_TIMEOUT_MS = 30_000
MAX_OUTPUT_TOKENS = 600
MEMO_COLUMNS = [
    "campaign",
    "metric",
    "segment",
    "control_n",
    "treatment_n",
    "control_rate",
    "treatment_rate",
    "absolute_lift",
    "relative_lift",
    "p_value",
    "ci_lower",
    "ci_upper",
    "result_label",
    "warning_label",
    "recommendation_label",
]


def generate_campaign_memo(
    filtered_results_df,
    selected_campaign,
    selected_metric,
    progress_callback=None,
) -> tuple[bool, str]:
    """Generate a concise memo from computed campaign lift results."""
    _log_status("generate_campaign_memo started.", progress_callback)
    _log_status(f"Selected campaign: {selected_campaign}", progress_callback)
    _log_status(f"Selected metric: {selected_metric}", progress_callback)

    row_count = 0 if filtered_results_df is None else len(filtered_results_df)
    _log_status(f"Rows received: {row_count}", progress_callback)

    api_key, key_source = _load_api_key(progress_callback)
    if not api_key:
        _log_status(
            "No API key found in system environment or .env.",
            progress_callback,
        )
        return (
            False,
            "Memo generation is unavailable because no GOOGLE_API_KEY or "
            "GEMINI_API_KEY was found in the system environment or local .env file.",
        )
    _log_status(f"API key found from {key_source}.", progress_callback)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        _log_status(
            "Google Gen AI SDK import failed: google-genai is not installed.",
            progress_callback,
        )
        return (
            False,
            "Memo generation is unavailable because google-genai is not installed. "
            "Run pip install google-genai or install requirements.txt.",
        )
    _log_status("Google Gen AI SDK import succeeded.", progress_callback)
    _log_status(f"Model name: {DEFAULT_MODEL_NAME}", progress_callback)
    _log_status(f"Request timeout: {REQUEST_TIMEOUT_MS} ms", progress_callback)

    if filtered_results_df is None or filtered_results_df.empty:
        _log_status(
            "No computed results available; aborting memo generation.",
            progress_callback,
        )
        return False, "No computed results are available for memo generation."

    prompt, prompt_source = _load_prompt()
    _log_status(
        f"Prompt loaded from {prompt_source}; character length: {len(prompt)}",
        progress_callback,
    )

    try:
        computed_summary = _format_results_for_prompt(filtered_results_df)
    except Exception as exc:
        _log_status(
            "Computed result formatting failed. "
            f"Error type: {exc.__class__.__name__}",
            progress_callback,
        )
        return False, f"Memo generation failed while formatting results: {exc}"

    _log_status(
        "Computed results formatted successfully; "
        f"summary character length: {len(computed_summary)}",
        progress_callback,
    )
    model_input = (
        f"{prompt}\n\n"
        "Computed campaign lift results follow. Use only these values.\n\n"
        f"Campaign: {selected_campaign}\n"
        f"Metric: {selected_metric}\n\n"
        f"{computed_summary}"
    )

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        _log_status("API request starting.", progress_callback)
        request_start = time.perf_counter()
        response = client.models.generate_content(
            model=DEFAULT_MODEL_NAME,
            contents=model_input,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        elapsed_seconds = time.perf_counter() - request_start
        _log_status(
            f"API request finished in {elapsed_seconds:.2f} seconds.",
            progress_callback,
        )
        memo_text = getattr(response, "text", "").strip()
    except Exception as exc:
        elapsed_seconds = (
            time.perf_counter() - request_start
            if "request_start" in locals()
            else 0.0
        )
        _log_status(
            "API request failed. "
            f"Elapsed seconds: {elapsed_seconds:.2f}; "
            f"error type: {exc.__class__.__name__}",
            progress_callback,
        )
        if _looks_like_timeout(exc):
            _log_status(
                "API request appears to have timed out.",
                progress_callback,
            )
            return (
                False,
                "Memo generation timed out after about 30 seconds. Please try again "
                "later or check your Google AI Studio API access.",
            )
        return False, f"Memo generation failed: {exc}"

    if not memo_text:
        _log_status(
            "Memo generation returned an empty response.",
            progress_callback,
        )
        return False, "Memo generation returned an empty response."

    _log_status(
        f"Memo generation succeeded; memo character length: {len(memo_text)}",
        progress_callback,
    )
    return True, memo_text


def _log_status(message: str, progress_callback=None) -> None:
    print(f"[memo_generator] {message}", flush=True)
    if progress_callback is not None:
        progress_callback(message)


def _looks_like_timeout(exc: Exception) -> bool:
    error_name = exc.__class__.__name__.lower()
    error_text = str(exc).lower()
    return "timeout" in error_name or "timed out" in error_text


def _load_api_key(progress_callback=None) -> tuple[str | None, str | None]:
    if os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY"), "system environment GOOGLE_API_KEY"
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY"), "system environment GEMINI_API_KEY"

    try:
        from dotenv import load_dotenv
    except ImportError:
        _log_status(
            "python-dotenv is not installed; skipping local .env lookup.",
            progress_callback,
        )
        return None, None

    load_dotenv(override=False)
    if os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY"), "local .env GOOGLE_API_KEY"
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY"), "local .env GEMINI_API_KEY"

    return None, None


def _load_prompt() -> tuple[str, str]:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8").strip(), str(PROMPT_PATH)
    except OSError:
        return (
            "Write a concise campaign lift memo for a marketing analyst. Use only "
            "the computed results provided. Do not recalculate statistics or invent "
            "missing information. Mention significance, confidence intervals, "
            "sample size warnings, and human review notes cautiously."
        ), "fallback prompt"


def _format_results_for_prompt(results_df: pd.DataFrame) -> str:
    available_columns = [col for col in MEMO_COLUMNS if col in results_df.columns]
    memo_df = results_df[available_columns].copy()

    formatted_rows = []
    for _, row in memo_df.iterrows():
        formatted_rows.append(
            {
                "campaign": _format_text(row.get("campaign", "")),
                "metric": _format_text(row.get("metric", "")),
                "segment": _format_text(row.get("segment", "")),
                "control_n": _format_count(row.get("control_n")),
                "treatment_n": _format_count(row.get("treatment_n")),
                "control_rate": _format_percent(row.get("control_rate")),
                "treatment_rate": _format_percent(row.get("treatment_rate")),
                "absolute_lift": _format_percentage_points(
                    row.get("absolute_lift")
                ),
                "relative_lift": _format_percent(
                    row.get("relative_lift"), signed=True
                ),
                "p_value": _format_p_value(row.get("p_value")),
                "ci_lower": _format_percentage_points(row.get("ci_lower")),
                "ci_upper": _format_percentage_points(row.get("ci_upper")),
                "result_label": _format_text(row.get("result_label", "")),
                "warning_label": _format_text(row.get("warning_label", "")),
                "recommendation_label": _format_text(
                    row.get("recommendation_label", "")
                ),
            }
        )

    return _records_to_markdown_table(formatted_rows)


def _records_to_markdown_table(records: list[dict[str, str]]) -> str:
    if not records:
        return "No rows available."

    headers = list(records[0].keys())
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = [
        "| " + " | ".join(str(record.get(header, "")) for header in headers) + " |"
        for record in records
    ]

    return "\n".join([header_row, separator_row, *body_rows])


def _format_text(value) -> str:
    if pd.isna(value):
        return ""

    return str(value).replace("|", "/").replace("\n", " ")


def _format_count(value) -> str:
    if pd.isna(value):
        return "N/A"

    return f"{float(value):,.0f}"


def _format_percent(value, signed: bool = False) -> str:
    if pd.isna(value):
        return "N/A"

    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.1%}"


def _format_percentage_points(value) -> str:
    if pd.isna(value):
        return "N/A"

    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f} pts"


def _format_p_value(value) -> str:
    if pd.isna(value):
        return "N/A"

    if value < 0.001:
        return "<0.001"

    return f"{value:.3f}"
