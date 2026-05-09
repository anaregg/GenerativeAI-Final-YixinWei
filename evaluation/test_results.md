# Test Results

## data/sample_campaign_results.csv

Expected behavior: The app should validate the standardized summary-level file, calculate lift statistics for each campaign + metric + segment pair, show charts, apply labels, and allow an optional memo to be generated from computed results.

What the app showed: The file passed validation. For `Spring Milk Campaign` and `Purchase Intent`, the Total segment showed Control rate 45.0%, Treatment rate 55.0%, absolute lift +10.0 pts, p-value 0.005, and the label `Significant positive lift`. Several segment-level results were significant positive lifts, while Male and Age 25-34 were directional positive results that were not statistically significant.

What worked: Validation, calculations, labels, summary cards, charts, confidence intervals, warning notes, and the detailed table worked for the sample file. The app clearly distinguished significant positive results from directional-only results.

What still requires human review: The app does not verify campaign design, random assignment, sample representativeness, or business context. Directional positive results should not be reported as confirmed lift without analyst review.

## data/evaluation_edge_cases.csv

Expected behavior: The app should still validate the file, calculate results, flag small samples, show negative or weak directional effects, and avoid overstating results.

What the app showed: The file passed validation. It included mixed results for `Landing Page Retargeting Campaign`. Purchase Intent Total was directional positive but not statistically significant. Purchase Intent Age 18-24 had a large observed lift but was labeled `Sample too small`. Brand Trust results were generally directional negative and not statistically significant. Ad Recall Returning Customers showed a significant positive lift.

What worked: The app handled small sample warnings, non-significant positive results, non-significant negative results, and a significant segment-level result. The warnings section made human review needs visible.

What still requires human review: Small segment results need careful interpretation. The app is strongest for standardized summary-level campaign lift interpretation, not raw survey analysis or causal proof. Analysts still need to evaluate test design, audience quality, and whether segment-level findings are appropriate to report.
