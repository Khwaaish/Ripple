# Adaption model evaluation

`data.evaluation` is a local evaluation framework for comparing genuine model
responses with engine-derived labels in `data/test.jsonl`. It performs no
inference and makes no Adaption API calls. The held-out test file is read only;
evaluation does not alter either dataset split.

## Prediction input format

Supply one JSON object per line with a test `scenario_id` and the model's raw
completion in a JSON string:

```json
{"scenario_id":"test-00900000","prediction":"{\"cascade_summary\":\"...\",\"direct_impacts\":[],\"second_order_impacts\":[],\"third_order_impacts\":[],\"further_impacts\":[],\"impacted_nodes\":[],\"predicted_bottleneck\":null,\"severity\":\"low\",\"ranked_mitigation_interventions\":[\"none\",\"reroute\",\"backup_supplier\",\"prioritize\"],\"recommended_intervention\":\"none\",\"explanation\":\"...\"}"}
```

The completion must follow the existing training contract from
`data.adaption_trial.prepare_trial`: `cascade_summary` and `explanation` are
strings; impact layers and impacted nodes are string arrays; bottleneck is a
string or null; severity is one of `low`, `medium`, `high`, `critical`; the
ranking contains each supported strategy once; recommendation is a supported
strategy. Responses must be strict JSON without Markdown fences. Duplicate
scenario IDs are ambiguous and invalidate that scenario. Missing, malformed,
incomplete, and non-test predictions are never treated as correct.

## Run

After a genuine model has produced a local JSONL predictions file:

```powershell
python -m data.evaluation --predictions data/evaluation/predictions.jsonl --model-id "<verified-model-id>"
```

The default aggregate-only report is written to
`data/evaluation/evaluation_report.json`. Predictions and reports under
`data/evaluation/` are ignored by Git. The report contains no per-scenario
answers or labels. Do not place credentials in prediction files.

Validate the local datasets without uploading or training:

```powershell
python -m data.validate_dataset --report data/evaluation/dataset_quality_report.json
```

## Metrics

Coverage metrics use every held-out sample. Accuracy and set metrics use only
complete, valid prediction objects, and the report records the denominator.
Impact-layer precision, recall, and F1 and affected-node Jaccard are macro
averages across scenarios; for empty-vs-empty sets, precision, recall, F1, and
Jaccard are 1. Downstream impact is the union of second-, third-, and
further-order nodes. Structured exact match requires exact agreement on all
impact sets/layers, bottleneck, severity, full strategy order, and selected
strategy; prose fields are excluded.

The model completion schema does not contain numeric `impact_score`, so MAE and
RMSE are explicitly reported as unavailable. They must not be inferred from
severity or prose. The current integration status is **pending** until the
active training run is complete and a verified model identifier/inference
interface is available.
