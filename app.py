from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.calculations import calculate_campaign_lift
from src.charts import (
    create_confidence_interval_chart,
    create_lift_by_segment_chart,
    create_rate_comparison_chart,
)
from src.labels import apply_interpretation_labels
from src.memo_generator import generate_campaign_memo
from src.validation import validate_input_data


SAMPLE_DATA_PATH = Path("data/sample_campaign_results.csv")
REQUIRED_COLUMNS = "campaign, metric, segment, group, n, success"


def main() -> None:
    st.set_page_config(page_title="Campaign Lift Interpreter", layout="wide")

    st.title("Campaign Lift Interpreter")
    st.write(
        "This app helps marketing analysts interpret standardized A/B-style "
        "campaign summary tables by calculating lift, significance, confidence "
        "intervals, and rule-based warnings."
    )

    df = load_data()
    if df is None:
        st.info(
            "Upload a campaign summary CSV or select the sample file to begin. "
            f"Required columns: {REQUIRED_COLUMNS}."
        )
        st.stop()

    with st.expander("Input Data Preview", expanded=False):
        st.caption(f"Required columns: {REQUIRED_COLUMNS}. Extra columns are ignored.")
        st.dataframe(df.head(20), width="stretch")

    is_valid, issues = validate_input_data(df)
    if not is_valid:
        st.subheader("Validation Issues")
        for issue in issues:
            st.error(issue)
        st.stop()

    st.success("Input data passed validation.")

    alpha, min_sample_size = render_sidebar_settings()
    results_df = calculate_campaign_lift(df, alpha=alpha)
    labeled_results_df = apply_interpretation_labels(
        results_df, alpha=alpha, min_sample_size=min_sample_size
    )

    selected_campaign, selected_metric, selected_segment = render_sidebar_filters(
        labeled_results_df
    )

    selected_row = get_selected_row(
        labeled_results_df, selected_campaign, selected_metric, selected_segment
    )
    if selected_row is None:
        st.warning("No calculated result matches the selected filters.")
        st.stop()

    st.divider()
    st.subheader("Selected Result Summary")
    st.caption(
        f"{selected_campaign} | {selected_metric} | Segment: {selected_segment}"
    )
    render_summary_cards(selected_row)
    render_interpretation_box(selected_row)

    st.divider()
    st.subheader("Charts")
    render_charts(
        labeled_results_df, selected_campaign, selected_metric, selected_segment
    )

    filtered_results_df = labeled_results_df[
        (labeled_results_df["campaign"] == selected_campaign)
        & (labeled_results_df["metric"] == selected_metric)
    ].copy()

    st.divider()
    st.subheader("Warnings and Human Review Notes")
    render_warning_panel(filtered_results_df)

    with st.expander("Detailed Results Table", expanded=False):
        render_results_table(filtered_results_df)

    st.divider()
    render_llm_memo_section(filtered_results_df, selected_campaign, selected_metric)


def load_data() -> pd.DataFrame | None:
    uploaded_file = st.file_uploader("Upload campaign summary CSV", type=["csv"])
    use_sample_file = st.checkbox("Load sample campaign results", value=True)

    if uploaded_file is not None:
        try:
            return pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Could not load uploaded CSV: {exc}")
            st.stop()

    if use_sample_file:
        try:
            return pd.read_csv(SAMPLE_DATA_PATH)
        except Exception as exc:
            st.error(f"Could not load sample CSV: {exc}")
            st.stop()

    return None


def render_sidebar_settings() -> tuple[float, int]:
    st.sidebar.header("Analysis Settings")
    alpha = st.sidebar.number_input(
        "Alpha",
        min_value=0.001,
        max_value=0.5,
        value=0.05,
        step=0.01,
        format="%.3f",
        help="Significance threshold used for p-values and confidence intervals.",
    )
    min_sample_size = st.sidebar.number_input(
        "Minimum sample size threshold",
        min_value=1,
        value=50,
        step=1,
        help="Rows below this group sample size are flagged for human review.",
    )

    return float(alpha), int(min_sample_size)


def render_sidebar_filters(results_df: pd.DataFrame) -> tuple[str, str, str]:
    st.sidebar.header("Filters")

    campaign_options = list(results_df["campaign"].drop_duplicates())
    selected_campaign = st.sidebar.selectbox("Campaign", campaign_options)

    metric_options = list(
        results_df.loc[
            results_df["campaign"] == selected_campaign, "metric"
        ].drop_duplicates()
    )
    selected_metric = st.sidebar.selectbox("Metric", metric_options)

    segment_options = list(
        results_df.loc[
            (results_df["campaign"] == selected_campaign)
            & (results_df["metric"] == selected_metric),
            "segment",
        ].drop_duplicates()
    )
    default_segment_index = (
        segment_options.index("Total") if "Total" in segment_options else 0
    )
    selected_segment = st.sidebar.selectbox(
        "Segment", segment_options, index=default_segment_index
    )

    return selected_campaign, selected_metric, selected_segment


def get_selected_row(
    results_df: pd.DataFrame,
    selected_campaign: str,
    selected_metric: str,
    selected_segment: str,
) -> pd.Series | None:
    filtered_df = results_df[
        (results_df["campaign"] == selected_campaign)
        & (results_df["metric"] == selected_metric)
        & (results_df["segment"] == selected_segment)
    ]

    if filtered_df.empty:
        return None

    return filtered_df.iloc[0]


def render_summary_cards(row: pd.Series) -> None:
    first_row = st.columns(5)
    first_row[0].metric("Control rate", format_percent(row["control_rate"]))
    first_row[1].metric("Treatment rate", format_percent(row["treatment_rate"]))
    first_row[2].metric(
        "Absolute lift", format_percentage_points(row["absolute_lift"])
    )
    first_row[3].metric(
        "Relative lift", format_percent(row["relative_lift"], signed=True)
    )
    first_row[4].metric("p-value", format_p_value(row["p_value"]))


def render_interpretation_box(row: pd.Series) -> None:
    result_label = row["result_label"]
    recommendation = row["recommendation_label"]
    warning = row["warning_label"] if pd.notna(row["warning_label"]) else ""

    message = (
        f"Result label: {result_label}\n\n"
        f"Recommendation: {recommendation}"
    )
    if str(warning).strip():
        message += f"\n\nWarning / human review note: {warning}"

    if str(warning).strip() or result_label in {
        "Significant negative lift",
        "Sample too small",
    }:
        st.warning(message)
    elif result_label == "Significant positive lift":
        st.success(message)
    else:
        st.info(message)


def render_charts(
    results_df: pd.DataFrame,
    selected_campaign: str,
    selected_metric: str,
    selected_segment: str,
) -> None:
    rate_chart = create_rate_comparison_chart(
        results_df, selected_campaign, selected_metric, selected_segment
    )
    lift_chart = create_lift_by_segment_chart(
        results_df, selected_campaign, selected_metric
    )

    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("**Treatment vs Control Rate**")
        if rate_chart is None:
            st.warning("No rate comparison chart is available for the selected filters.")
        else:
            st.plotly_chart(rate_chart, width="stretch")

    with right_col:
        st.markdown("**Lift by Segment**")
        if lift_chart is None:
            st.warning("No lift by segment chart is available for the selected filters.")
        else:
            st.plotly_chart(lift_chart, width="stretch")

    ci_chart = create_confidence_interval_chart(
        results_df, selected_campaign, selected_metric
    )
    st.markdown("**Confidence Interval by Segment**")
    if ci_chart is None:
        st.warning("No confidence interval chart is available for the selected filters.")
    else:
        st.plotly_chart(ci_chart, width="stretch")


def render_results_table(filtered_results_df: pd.DataFrame) -> None:
    table_columns = [
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
    display_df = filtered_results_df[table_columns].copy()

    st.dataframe(
        display_df.style.format(
            {
                "control_n": "{:,.0f}",
                "treatment_n": "{:,.0f}",
                "control_rate": "{:.1%}",
                "treatment_rate": "{:.1%}",
                "absolute_lift": format_percentage_points,
                "relative_lift": lambda value: format_percent(value, signed=True),
                "p_value": format_p_value,
                "ci_lower": format_percentage_points,
                "ci_upper": format_percentage_points,
            }
        ),
        width="stretch",
    )


def render_warning_panel(filtered_results_df: pd.DataFrame) -> None:
    warning_rows = filtered_results_df[
        filtered_results_df["warning_label"].fillna("").str.strip() != ""
    ].copy()

    if warning_rows.empty:
        st.info("No warnings for the selected campaign and metric.")
        return

    st.warning("Some results need extra care before reporting.")
    st.dataframe(
        warning_rows[
            [
                "segment",
                "result_label",
                "warning_label",
                "recommendation_label",
            ]
        ],
        width="stretch",
    )


def render_llm_memo_section(
    filtered_results_df: pd.DataFrame, selected_campaign: str, selected_metric: str
) -> None:
    st.subheader("LLM Interpretation Memo")
    st.caption(
        "Optional: generate a concise memo from the computed results shown above. "
        "The model is not used for validation or statistical calculation."
    )
    st.info(
        "Memo generation may take a few seconds. Progress details are shown "
        "below and printed in the terminal running Streamlit. The model is "
        "called only when this button is clicked."
    )

    if st.button("Generate Interpretation Memo"):
        print("[app] Generate Interpretation Memo button clicked.", flush=True)
        progress_messages = ["Button clicked."]
        success = False
        message = ""

        with st.status("Generating memo...", expanded=True) as status:
            progress_box = st.empty()
            progress_box.markdown(format_progress_messages(progress_messages))

            def update_progress(progress_message: str) -> None:
                progress_messages.append(progress_message)
                progress_box.markdown(format_progress_messages(progress_messages))

            with st.spinner("Generating memo from computed results..."):
                success, message = generate_campaign_memo(
                    filtered_results_df,
                    selected_campaign,
                    selected_metric,
                    progress_callback=update_progress,
                )

            if success:
                status.update(label="Memo generated.", state="complete", expanded=False)
            else:
                status.update(
                    label="Memo generation stopped.",
                    state="error",
                    expanded=True,
                )

        if success:
            st.markdown(format_memo_for_display(message))
        else:
            st.warning(message)


def format_memo_for_display(memo_text: str) -> str:
    formatted_lines = []

    for line in memo_text.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            heading_text = stripped_line.lstrip("#").strip()
            if heading_text:
                formatted_lines.append(f"**{heading_text}**")
            continue

        formatted_lines.append(line)

    return "\n".join(formatted_lines)


def format_progress_messages(messages: list[str]) -> str:
    return "\n".join(f"- {message}" for message in messages)


def format_percent(value, signed: bool = False) -> str:
    if pd.isna(value):
        return "N/A"

    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.1%}"


def format_percentage_points(value) -> str:
    if pd.isna(value):
        return "N/A"

    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f} pts"


def format_p_value(value) -> str:
    if pd.isna(value):
        return "N/A"

    if value < 0.001:
        return "<0.001"

    return f"{value:.3f}"


if __name__ == "__main__":
    main()
