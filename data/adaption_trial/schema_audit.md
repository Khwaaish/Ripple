# Batch 3 schema audit

## Source inspection

The source is `data/train.jsonl`, generated and validated by Batch 2. Each record contains scenario metadata, a serialized network, `ground_truth.baseline`, `ground_truth.interventions`, recommendation fields, and `ai_target`. `ai_target` has these keys: `cascade_summary`, `direct_impacts`, `second_order_impacts`, `third_order_impacts`, `further_impacts`, `predicted_bottleneck`, `severity`, `ranked_mitigation_interventions`, `explanation`, and `structured_response`.

Batch 2's validator recomputes baseline and all four intervention results from the saved network and failed nodes, then compares the AI target's impact layers, bottleneck, severity, ranking, summary, and explanation against engine outputs. Thus the target labels and the numbers embedded in its summary are engine-derived. The short explanation is composed from the engine's impacted-node count, critical-shortage count, comparison ranking, and recommendation reason.

## Training suitability and conversion choices

- The full baseline and intervention analyses are valuable audit data but redundant as training completion: the AI target already contains the requested answer. They are excluded from the prompt and completion to prevent label leakage and answer duplication.
- `structured_response` in `ai_target` repeats its summary, impacted nodes, bottleneck, severity, recommendation, and ranking. The converter emits those same values once in a flat JSON completion. It does not change any label value or edit the source dataset.
- Scenario IDs, seeds, split labels, generator difficulty, and raw failure descriptions are metadata. The prompt includes failure type, failed node IDs, and the compact network; source IDs remain in `trial_metadata.json`, not in the model answer.
- Optional `unit_cost` is omitted from prompt network nodes because Batch 1 simulation and intervention ranking do not use it. Capacity, load, buffer, criticality, recovery time, and edge properties are retained because they describe the network semantics used by the engine.
- The current model is deliberately simplified. A generated summary should be interpreted as the engine's modeled result, not a real-world logistics forecast. Training instructions prohibit adding unsupported claims.

## Split isolation

The converter reads only the fixed `data/train.jsonl` path and refuses any selected row whose `split` is not `train`. It never opens or accepts a test-file path. The 50 selected IDs and the training source path are recorded in the trial metadata. No source labels or engine behavior are changed.

## Adaption interface audit

The installed environment has `adaption` version **0.19.0**. Local signature inspection confirmed:

- `datasets.upload_file(path, *, name=None, processing_mode=None, column_mapping=None)`
- `datasets.get_status(dataset_id)` and `datasets.get(dataset_id)`
- `datasets.wait_for_completion(dataset_id, *, initial_interval=2.0, max_interval=30.0, backoff_factor=2.0, timeout=3600.0)`
- `datasets.adapt(dataset_id, *, column_mapping=..., ..., estimate=...)`

The client utility uses `upload_file` with `processing_mode="raw"` and `{"prompt": "prompt", "completion": "completion"}` mapping, then checks status, row count, and configured mapping. Cost quotation uses only `datasets.adapt(..., estimate=True)`. There is no code path to call adaptation with `estimate=False` or AutoScientist.

These SDK calls follow the [official file upload and import guide](https://docs.adaptionlabs.ai/adaptive-data-quickstart), [official create dataset reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/create), [official dataset status reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/get_status), [official estimate-only Adaptive Data reference](https://docs.adaptionlabs.ai/api/python/resources/datasets/methods/adapt/), and [column mapping guide](https://docs.adaptionlabs.ai/adaptive-data/select-columns/). The docs say `estimate=True` returns a quote without starting a run; it may save the mapping used to price the estimate.

No API request, upload, estimate, adaptation, or AutoScientist run was made during this batch.
