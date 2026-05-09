from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


GROUP_KEYS = ["campaign", "metric", "segment"]


def calculate_campaign_lift(df, alpha=0.05) -> pd.DataFrame:
    """Calculate treatment/control lift statistics for validated summary data."""
    working_df = df.copy()
    working_df["n"] = pd.to_numeric(working_df["n"])
    working_df["success"] = pd.to_numeric(working_df["success"])

    rows = []

    for keys, group_df in working_df.groupby(GROUP_KEYS, sort=False):
        control = group_df[group_df["group"] == "Control"].iloc[0]
        treatment = group_df[group_df["group"] == "Treatment"].iloc[0]

        control_n = float(control["n"])
        control_success = float(control["success"])
        treatment_n = float(treatment["n"])
        treatment_success = float(treatment["success"])

        control_rate = control_success / control_n
        treatment_rate = treatment_success / treatment_n
        absolute_lift = treatment_rate - control_rate
        relative_lift = (
            absolute_lift / control_rate if control_rate != 0 else np.nan
        )

        standard_error = np.sqrt(
            (control_rate * (1 - control_rate) / control_n)
            + (treatment_rate * (1 - treatment_rate) / treatment_n)
        )
        z_score, p_value = _calculate_z_test(
            absolute_lift,
            control_success,
            control_n,
            treatment_success,
            treatment_n,
            standard_error,
        )

        z_critical = norm.ppf(1 - alpha / 2)
        margin_of_error = z_critical * standard_error

        rows.append(
            {
                "campaign": keys[0],
                "metric": keys[1],
                "segment": keys[2],
                "control_n": control_n,
                "control_success": control_success,
                "treatment_n": treatment_n,
                "treatment_success": treatment_success,
                "control_rate": control_rate,
                "treatment_rate": treatment_rate,
                "absolute_lift": absolute_lift,
                "relative_lift": relative_lift,
                "standard_error": standard_error,
                "z_score": z_score,
                "p_value": p_value,
                "ci_lower": absolute_lift - margin_of_error,
                "ci_upper": absolute_lift + margin_of_error,
            }
        )

    return pd.DataFrame(rows)


def _calculate_z_test(
    absolute_lift: float,
    control_success: float,
    control_n: float,
    treatment_success: float,
    treatment_n: float,
    fallback_standard_error: float,
) -> tuple[float, float]:
    pooled_rate = (control_success + treatment_success) / (control_n + treatment_n)
    pooled_standard_error = np.sqrt(
        pooled_rate * (1 - pooled_rate) * ((1 / control_n) + (1 / treatment_n))
    )

    if pooled_standard_error > 0:
        z_score = absolute_lift / pooled_standard_error
        p_value = 2 * (1 - norm.cdf(abs(z_score)))
        return z_score, p_value

    if fallback_standard_error > 0:
        z_score = absolute_lift / fallback_standard_error
        p_value = 2 * (1 - norm.cdf(abs(z_score)))
        return z_score, p_value

    if absolute_lift == 0:
        return 0.0, 1.0

    return np.nan, 0.0
