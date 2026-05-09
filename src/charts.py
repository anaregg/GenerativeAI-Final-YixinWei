from __future__ import annotations

import plotly.graph_objects as go


def create_rate_comparison_chart(
    results_df, selected_campaign, selected_metric, selected_segment
):
    filtered_df = _filter_results(
        results_df, selected_campaign, selected_metric, selected_segment
    )
    if filtered_df.empty:
        return None

    row = filtered_df.iloc[0]
    groups = ["Control", "Treatment"]
    rates = [row["control_rate"], row["treatment_rate"]]

    fig = go.Figure(
        data=[
            go.Bar(
                x=groups,
                y=rates,
                text=[f"{rate:.1%}" for rate in rates],
                textposition="auto",
                marker_color=["#4C78A8", "#F58518"],
                hovertemplate="%{x} Rate: %{y:.1%}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=f"{selected_metric}: Control vs Treatment Rate ({selected_segment})",
        xaxis_title="Group",
        yaxis_title="Rate",
        template="plotly_white",
        showlegend=False,
    )
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")

    return fig


def create_lift_by_segment_chart(results_df, selected_campaign, selected_metric):
    filtered_df = _filter_results(results_df, selected_campaign, selected_metric)
    if filtered_df.empty:
        return None

    fig = go.Figure(
        data=[
            go.Bar(
                x=filtered_df["segment"],
                y=filtered_df["absolute_lift"],
                marker_color=[
                    "#54A24B" if lift >= 0 else "#E45756"
                    for lift in filtered_df["absolute_lift"]
                ],
                hovertemplate=(
                    "Segment: %{x}<br>"
                    "Absolute lift: %{y:.1%}<extra></extra>"
                ),
            )
        ]
    )

    fig.add_hline(y=0, line_width=1, line_color="#444444")
    fig.update_layout(
        title=f"{selected_metric}: Absolute Lift by Segment",
        xaxis_title="Segment",
        yaxis_title="Absolute Lift (percentage points)",
        template="plotly_white",
        showlegend=False,
    )
    fig.update_yaxes(tickformat=".0%")

    return fig


def create_confidence_interval_chart(results_df, selected_campaign, selected_metric):
    filtered_df = _filter_results(results_df, selected_campaign, selected_metric)
    if filtered_df.empty:
        return None

    error_above = filtered_df["ci_upper"] - filtered_df["absolute_lift"]
    error_below = filtered_df["absolute_lift"] - filtered_df["ci_lower"]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=filtered_df["segment"],
                y=filtered_df["absolute_lift"],
                mode="markers",
                marker={
                    "color": [
                        "#54A24B" if lift >= 0 else "#E45756"
                        for lift in filtered_df["absolute_lift"]
                    ],
                    "size": 10,
                },
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": error_above.to_numpy(),
                    "arrayminus": error_below.to_numpy(),
                    "visible": True,
                    "thickness": 1.5,
                },
                hovertemplate=(
                    "Segment: %{x}<br>"
                    "Absolute lift: %{y:.1%}<br>"
                    "CI lower: %{customdata[0]:.1%}<br>"
                    "CI upper: %{customdata[1]:.1%}<extra></extra>"
                ),
                customdata=filtered_df[["ci_lower", "ci_upper"]].to_numpy(),
            )
        ]
    )

    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="#444444")
    fig.update_layout(
        title=f"{selected_metric}: Absolute Lift with Confidence Intervals",
        xaxis_title="Segment",
        yaxis_title="Absolute Lift (percentage points)",
        template="plotly_white",
        showlegend=False,
    )
    fig.update_yaxes(tickformat=".0%")

    return fig


def _filter_results(
    results_df, selected_campaign, selected_metric, selected_segment=None
):
    mask = (
        (results_df["campaign"] == selected_campaign)
        & (results_df["metric"] == selected_metric)
    )

    if selected_segment is not None:
        mask = mask & (results_df["segment"] == selected_segment)

    return results_df.loc[mask].copy()
