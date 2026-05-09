# Campaign Lift Interpreter

## Project Context

Campaign Lift Interpreter is a Streamlit app for junior marketing analysts who need to interpret standardized A/B-style campaign test summaries. The app supports a common reporting workflow: an analyst receives a summary table, checks whether Treatment outperformed Control, reviews statistical confidence, and prepares a short business interpretation.

The app does not process raw respondent-level survey data and does not try to be a general marketing analytics assistant. It focuses on one repeatable task: interpreting campaign lift from a standardized summary-level CSV.

## What the App Does

The app workflow is:

1. Upload a CSV file or load the included sample data.
2. Validate the input structure and values.
3. Calculate treatment/control rates, absolute lift, relative lift, p-values, and confidence intervals.
4. Apply deterministic rule-based labels and warnings.
5. Display summary cards, charts, warnings, and a detailed results table.
6. Optionally generate a concise interpretation memo from the computed results.

## Why Generative AI Is Useful Here

Generative AI is not used for statistics in this project. Python performs validation, calculations, labels, and chart generation.

The LLM is used only after the calculations are complete. Its role is to turn computed outputs into a readable analyst memo. This helps a junior analyst explain results clearly while keeping the memo grounded in deterministic Python outputs.

## Input Format

The required CSV columns are:

```csv
campaign,metric,segment,group,n,success
```

Example row:

```csv
Spring Milk Campaign,Purchase Intent,Total,Control,400,180
```

Each campaign + metric + segment combination must have exactly one `Control` row and one `Treatment` row. Extra columns are ignored.

## System Design

- `app.py`: Streamlit dashboard, file loading, filters, summary display, warnings, tables, charts, and optional memo button.
- `src/validation.py`: validates required columns, numeric values, groups, duplicates, and Control/Treatment pairing.
- `src/calculations.py`: calculates rates, lift, p-values, z-scores, standard errors, and confidence intervals.
- `src/labels.py`: applies deterministic result labels, warnings, and recommendations.
- `src/charts.py`: creates Plotly charts for rate comparison, lift by segment, and confidence intervals.
- `src/memo_generator.py`: optionally calls Gemini using `google-genai` and sends only computed/labeled results.
- `prompts/campaign_memo_prompt.md`: prompt that constrains the memo to computed results and cautious interpretation.

## Artifact Snapshot

The Streamlit app includes:
- a file upload / sample data loader
- input validation messages
- selected result summary cards
- Treatment vs Control rate chart
- lift by segment chart
- confidence interval chart
- warning and human review notes
- optional LLM interpretation memo

## Baseline Comparison

The baseline workflow is spreadsheet-based. An analyst manually prepares a summary table, calculates control/treatment rates, calculates lift, checks significance manually or skips it, creates charts, and writes a memo.

This app improves consistency by packaging validation, statistical calculation, visualization, rule-based warnings, and optional memo generation into one workflow.

## Evaluation

The app was evaluated with:

- `data/sample_campaign_results.csv`: standard campaign results with positive and directional effects.
- `data/evaluation_edge_cases.csv`: small samples, weak effects, negative directional effects, and mixed segment results.

Evaluation criteria include calculation correctness, visualization usefulness, memo faithfulness, decision caution, and actionability.

## Setup

```bash
pip install -r requirements.txt
```

## API Key Setup

The dashboard works without an API key. Without a key, validation, calculations, charts, warnings, and tables still run. Only the optional LLM memo is unavailable.

The memo feature requires one of these environment variables:

```bash
GOOGLE_API_KEY
GEMINI_API_KEY
```

The app first checks system environment variables. If neither key exists, it tries a local `.env` file. The `.env` file should not be committed. `.env.example` is only a template.

## Run the App

```bash
python -m streamlit run app.py
```

## Limitations and Human Review

- The app only supports standardized summary-level CSVs.
- It does not process raw respondent-level survey data.
- It does not prove causality unless the underlying test design supports that claim.
- The LLM memo is a first-draft interpretation, not a final report.
- Human analysts should review sample quality, test design, audience definitions, and business context before reporting results.
