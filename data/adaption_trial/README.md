# Adaption 50-row trial

This folder contains a reproducible, training-only conversion trial for review before any larger use.

## Local-only preparation (default)

From the repository root, run:

```bash
python -m data.adaption_trial.prepare_trial
```

The command reads only the fixed `data/train.jsonl` path, selects exactly 50 records with seed `5102026`, converts them to JSONL rows with exactly `prompt` and `completion`, writes `trial_metadata.json`, and writes a safe local report. It checks that every source row is training data and that each selected completion exactly matches a projection of that source row's engine-derived `ai_target`.

The completion contains a concise flat JSON object with cascade summary, propagation layers, impacted node IDs, predicted bottleneck, severity, ranked strategies, recommendation, and explanation. Redundant `structured_response` nesting is flattened without changing any values. The prompt includes network inputs and failure metadata, not ground-truth analysis.

## Explicit Adaption actions

The installed SDK was inspected before implementing the client. Upload only the trial file with:

```bash
python -m data.adaption_trial.prepare_trial --upload
```

This uses `ADAPTION_API_KEY` (the existing `.env` is loaded without printing it) and uploads as `processing_mode="raw"`, mapping `prompt` to `prompt` and `completion` to `completion`. It verifies the imported row count and configured column mapping, then updates `safe_trial_report.json`.

To upload and request an estimate-only Adaptive Data quote, both flags are required:

```bash
python -m data.adaption_trial.prepare_trial --upload --estimate
```

The quote uses `datasets.adapt(..., estimate=True)`. If an upload succeeded but a later estimate needs retrying, use `--estimate --dataset-id <id>` with the ID already saved in `safe_trial_report.json`; the utility checks that ID, row count, selected IDs, source split, and local file hash before quoting. There is no CLI path to run a paid adaptation or launch AutoScientist. The estimate endpoint may save the column mapping used for the quote; it does not launch a run. The held-out `data/test.jsonl` file is never read by this utility and cannot be passed as an input.

## Files

- `schema_audit.md`: source-target and API interface audit.
- `ripple_trial_50.jsonl`: converted prompt/completion examples.
- `trial_metadata.json`: selection seed, source, version, IDs, diversity counts, and file hash.
- `safe_trial_report.json`: local validation/API status with no secret values.
- `prepare_trial.py`: deterministic converter and CLI.
- `adaption_trial_client.py`: upload, ingestion verification, and estimate-only functions.

Run the full test suite with `python -m pytest`. No upload or estimate is performed by default.

## Batch 4: 50-row adaptation trial plan

The `run_adaptation_trial.py` runner validates the already ingested 50-row training-only dataset and requests a fresh **estimate-only** quote by default. The held-out test split is never read or uploaded. The plan uses the existing dataset ID from `safe_trial_report.json`, maps `prompt` and `completion`, sets `max_rows=50`, and enables deduplication only. Prompt rephrasing and reasoning traces remain disabled to protect structured inputs and exact targets.

Run the plan and write review artifacts with:

```bash
python -m data.adaption_trial.run_adaptation_trial
```

This creates local-only plan and quality artifacts; reports and dataset IDs are not intended for source control. The quality and examples files explicitly say no adaptation was run; no adapted JSONL is created. A fresh estimate that differs from the estimate saved in your local trial report blocks the explicit run path. A dataset record that already contains a run ID is also left for manual review even if the estimate is confirmed. The saved report and dataset ID must remain local and are excluded from the public repository. After reviewing the plan, a user can manually submit exactly one paid request with:

```bash
python -m data.adaption_trial.run_adaptation_trial --run-adaptation
```

That explicit path uses a single request with SDK retries disabled and records the attempt before submission to block accidental second runs. It does not launch AutoScientist or train a model. A completed output is downloaded only after a successful status and compared using exact original prompt or prompt/completion matching; no fuzzy or order-only row matching is used.

The runner follows the [official `datasets.adapt` reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/adapt) for estimate and recipe configuration, the [dataset status reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/get_status) for ingestion checks, and the [download reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/download) for processed JSONL retrieval.
