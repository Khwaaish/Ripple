# Batch 2: scenarios and datasets

This pipeline generates synthetic supply-chain networks and disruption scenarios, runs them through Ripple's deterministic engine, and writes engine-derived labels. It makes no AI or Adaption API calls.

## Generate

From the repository root:

```bash
python -m data.generate_dataset
```

Defaults produce 2,000 training scenarios in `train.jsonl` and 300 held-out scenarios in `test.jsonl`. The train seed range starts at 100000; the independent test range starts at 900000. Re-running with identical arguments reproduces the same JSONL bytes. To generate a smaller fixture, pass `--train-count`, `--test-count`, and optionally seed starts or `--output-dir`.

Networks vary from 6 to 12 nodes and use hub, regional, mesh, and ladder supply topologies. Node counts, loads, capacities, buffers, criticality, edge shares, reliability, delays, single or multiple failures are seeded. Difficulty is assigned from network size, edge density, and number of failed nodes. Severity is never assigned by the generator: it is computed by `engine.simulate`.

## Record schema

Each JSONL record has:

- Scenario metadata: `scenario_id`, `seed`, `split`, `difficulty`, `network`, `failed_nodes`, `failure_type`, `failure_description`.
- `ground_truth.baseline`: cascade layers, direct/second/third/further impacts, node shortages, overloads, critical shortages, bottleneck, stockout time, propagation rounds, impact score, severity, recovery estimate, snapshots, and reasoning.
- `ground_truth.interventions`: engine comparison for `none`, `reroute`, `backup_supplier`, and `prioritize`, including disrupted/critical/overloaded nodes, score, recovery, costs, ratios against baseline, relative improvement, and reasoning.
- `ground_truth.recommendation_*`: engine ranking, selected strategy, and its tie-break explanation.
- `ai_target`: a separate concise summary, impact layers, bottleneck, severity, intervention ranking, explanation, and structured response. These values are projections of the engine results; no model-generated labels or claims are included.

## Validate and report

```bash
python -m data.validate_dataset
```

The validator parses JSONL, checks schema and finite values, validates each network and failure set, checks split counts and ID leakage, detects duplicate canonical network/failure combinations, and recomputes baseline and intervention labels from the engine. It writes `dataset_quality_report.json` with counts, distributions, validation failures, and diversity warnings. Small fixtures can override expected row counts with `--expected-train` and `--expected-test`.

The canonical duplicate definition is the SHA-256 of the serialized network and sorted failed-node IDs, excluding seed, split, ID, and output labels. Test records remain in `test.jsonl`; the pipeline does not upload or otherwise send either split to Adaption.
