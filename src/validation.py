from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ["campaign", "metric", "segment", "group", "n", "success"]
SUPPORTED_GROUPS = {"Control", "Treatment"}
GROUP_KEYS = ["campaign", "metric", "segment"]
ROW_KEYS = GROUP_KEYS + ["group"]


def validate_input_data(df) -> tuple[bool, list[str]]:
    """Validate a standardized campaign summary DataFrame."""
    issues: list[str] = []

    if df is None or not isinstance(df, pd.DataFrame):
        return False, ["Input must be a pandas DataFrame."]

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        issues.append(
            "Missing required column(s): " + ", ".join(missing_columns) + "."
        )

    present_required = [col for col in REQUIRED_COLUMNS if col in df.columns]
    if not present_required:
        return False, issues

    _check_missing_values(df, present_required, issues)
    _check_numeric_fields(df, issues)
    _check_group_values(df, issues)
    _check_pair_completeness(df, issues)
    _check_duplicate_rows(df, issues)

    return len(issues) == 0, issues


def _check_missing_values(
    df: pd.DataFrame, columns: list[str], issues: list[str]
) -> None:
    for column in columns:
        missing_count = int(df[column].isna().sum())
        if missing_count > 0:
            issues.append(
                f"Column '{column}' has {missing_count} missing value(s)."
            )


def _check_numeric_fields(df: pd.DataFrame, issues: list[str]) -> None:
    if "n" not in df.columns or "success" not in df.columns:
        return

    numeric_n = pd.to_numeric(df["n"], errors="coerce")
    numeric_success = pd.to_numeric(df["success"], errors="coerce")

    invalid_n_count = int(numeric_n.isna().sum() - df["n"].isna().sum())
    invalid_success_count = int(
        numeric_success.isna().sum() - df["success"].isna().sum()
    )

    if invalid_n_count > 0:
        issues.append(f"Column 'n' has {invalid_n_count} non-numeric value(s).")
    if invalid_success_count > 0:
        issues.append(
            f"Column 'success' has {invalid_success_count} non-numeric value(s)."
        )

    valid_n = numeric_n.notna()
    valid_success = numeric_success.notna()
    valid_both = valid_n & valid_success

    non_positive_n_count = int((valid_n & (numeric_n <= 0)).sum())
    negative_success_count = int((valid_success & (numeric_success < 0)).sum())
    too_many_successes_count = int(
        (valid_both & (numeric_success > numeric_n)).sum()
    )

    if non_positive_n_count > 0:
        issues.append(f"Column 'n' has {non_positive_n_count} value(s) <= 0.")
    if negative_success_count > 0:
        issues.append(
            f"Column 'success' has {negative_success_count} value(s) < 0."
        )
    if too_many_successes_count > 0:
        issues.append(
            "'success' exceeds 'n' in "
            f"{too_many_successes_count} row(s)."
        )


def _check_group_values(df: pd.DataFrame, issues: list[str]) -> None:
    if "group" not in df.columns:
        return

    non_missing_groups = df["group"].dropna()
    invalid_groups = sorted(
        str(group)
        for group in non_missing_groups.unique()
        if group not in SUPPORTED_GROUPS
    )

    if invalid_groups:
        issues.append(
            "Unsupported group value(s): "
            + ", ".join(invalid_groups)
            + ". Only Control and Treatment are supported."
        )


def _check_pair_completeness(df: pd.DataFrame, issues: list[str]) -> None:
    if any(column not in df.columns for column in ROW_KEYS):
        return

    clean_df = df.dropna(subset=ROW_KEYS)

    for keys, group_df in clean_df.groupby(GROUP_KEYS, dropna=False):
        observed_groups = set(group_df["group"]) & SUPPORTED_GROUPS
        missing_groups = sorted(SUPPORTED_GROUPS - observed_groups)
        if missing_groups:
            issues.append(
                _format_group_key(keys)
                + " is missing required group(s): "
                + ", ".join(missing_groups)
                + "."
            )


def _check_duplicate_rows(df: pd.DataFrame, issues: list[str]) -> None:
    if any(column not in df.columns for column in ROW_KEYS):
        return

    clean_df = df.dropna(subset=ROW_KEYS)
    duplicate_counts = (
        clean_df.groupby(ROW_KEYS, dropna=False).size().reset_index(name="row_count")
    )
    duplicate_counts = duplicate_counts[duplicate_counts["row_count"] > 1]

    for _, row in duplicate_counts.iterrows():
        keys = tuple(row[column] for column in GROUP_KEYS)
        issues.append(
            _format_group_key(keys)
            + f" has duplicate rows for group '{row['group']}'."
        )


def _format_group_key(keys: tuple) -> str:
    campaign, metric, segment = keys
    return f"Campaign '{campaign}', metric '{metric}', segment '{segment}'"
