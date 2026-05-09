from __future__ import annotations

import pandas as pd


def apply_interpretation_labels(
    results_df, alpha=0.05, min_sample_size=50
) -> pd.DataFrame:
    """Add deterministic interpretation labels to calculated lift results."""
    labeled_df = results_df.copy()

    labels = labeled_df.apply(
        lambda row: _label_row(row, alpha, min_sample_size),
        axis=1,
        result_type="expand",
    )
    labels.columns = ["result_label", "warning_label", "recommendation_label"]

    return pd.concat([labeled_df, labels], axis=1)


def _label_row(
    row: pd.Series, alpha: float, min_sample_size: int
) -> tuple[str, str, str]:
    if row["control_n"] < min_sample_size or row["treatment_n"] < min_sample_size:
        return (
            "Sample too small",
            "Interpret with caution: sample size is below threshold.",
            "Needs human review",
        )

    if row["p_value"] < alpha and row["absolute_lift"] > 0:
        return (
            "Significant positive lift",
            "",
            "Report as positive lift",
        )

    if row["p_value"] < alpha and row["absolute_lift"] < 0:
        return (
            "Significant negative lift",
            "Treatment underperformed control.",
            "Investigate before reporting",
        )

    if row["absolute_lift"] > 0:
        return (
            "Directional positive lift, not statistically significant",
            "Do not overstate this result.",
            "Use as directional evidence only",
        )

    if row["absolute_lift"] < 0:
        return (
            "Directional negative lift, not statistically significant",
            "Do not overstate this result.",
            "Monitor or investigate further",
        )

    return (
        "No clear difference",
        "No observed lift.",
        "Do not report as a meaningful lift",
    )
