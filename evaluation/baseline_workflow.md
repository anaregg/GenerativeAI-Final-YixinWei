# Baseline Workflow

The baseline for this project is a spreadsheet-based campaign analysis workflow.

In the baseline process, a marketing analyst manually:

1. Prepares a summary table for each campaign, KPI metric, audience segment, and test group.
2. Calculates Control and Treatment rates from `success / n`.
3. Calculates absolute lift and relative lift.
4. Checks statistical significance manually, inconsistently, or sometimes skips the check.
5. Creates charts in a spreadsheet or slide deck.
6. Writes a short interpretation memo for stakeholders.

This manual workflow is familiar but fragile. It can lead to inconsistent formulas, missing significance checks, unclear warnings, and memos that overstate directional results.

Campaign Lift Interpreter improves the workflow by combining validation, deterministic calculations, rule-based labels, Plotly visualizations, warnings, and optional memo generation in one repeatable Streamlit app. The goal is not to replace analyst judgment, but to make the first-pass interpretation more consistent and easier to review.
