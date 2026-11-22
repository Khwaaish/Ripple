"""Convert a seeded, training-only selection into instruction/completion JSONL."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import random
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = ROOT / "data" / "train.jsonl"
TRIAL_DIR = ROOT / "data" / "adaption_trial"
TRIAL_PATH = TRIAL_DIR / "ripple_trial_50.jsonl"
METADATA_PATH = TRIAL_DIR / "trial_metadata.json"
REPORT_PATH = TRIAL_DIR / "safe_trial_report.json"
SELECTION_SEED = 510_2026
CONVERSION_VERSION = "1.0.0"
TRIAL_SIZE = 50

INSTRUCTION = """You are Ripple, an analyst of cascading supply-chain failures. Analyze the provided network and disruption using only the supplied information. Distinguish direct, second-order, third-order, and further propagation. Identify the bottleneck and severity. Rank the mitigation strategies none, reroute, backup_supplier, and prioritize based on the scenario. Do not invent facts, numbers, or causal claims unsupported by the network. Return strictly valid JSON matching the requested schema, with no Markdown or extra text."""
COMPLETION_KEYS = (
    "cascade_summary", "direct_impacts", "second_order_impacts", "third_order_impacts",
    "further_impacts", "impacted_nodes", "predicted_bottleneck", "severity",
    "ranked_mitigation_interventions", "recommended_intervention", "explanation",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load nonblank JSONL objects with line-specific errors."""
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"Blank JSONL line {line_no} in {path}")
            try:
                value = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"Invalid JSON on line {line_no} in {path}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL line {line_no} in {path} must be an object")
            rows.append(value)
    return rows


def _topology(description: str) -> str:
    try:
        return description.split("in a ", 1)[1].split()[0]
    except (IndexError, AttributeError):
        return "unknown"


def _quota(counts: Counter[str], total: int) -> dict[str, int]:
    """Allocate proportional integer quotas, giving represented groups one seat."""
    if not counts:
        return {}
    raw = {key: total * value / sum(counts.values()) for key, value in counts.items()}
    targets = {key: max(1, int(value)) for key, value in raw.items()}
    while sum(targets.values()) > total:
        reducible = [key for key in targets if targets[key] > 1]
        if not reducible:
            break
        key = min(reducible, key=lambda k: (raw[k] - int(raw[k]), raw[k], k))
        targets[key] -= 1
    while sum(targets.values()) < total:
        key = max(raw, key=lambda k: (raw[k] - int(raw[k]), raw[k], k))
        targets[key] += 1
        raw[key] = int(raw[key])
    return targets


def select_trial_records(records: list[dict[str, Any]], *, count: int = TRIAL_SIZE,
                         seed: int = SELECTION_SEED) -> list[dict[str, Any]]:
    """Select a seeded, diversity-aware sample from training rows only."""
    if count < 1 or len(records) < count:
        raise ValueError(f"Need at least {count} training records")
    if any(row.get("split") != "train" for row in records):
        raise ValueError("Trial source contains a non-training row; test data is not eligible")
    if any(not isinstance(row.get("scenario_id"), str) or not row["scenario_id"] for row in records):
        raise ValueError("Every training row must have a scenario_id")
    ids = [row["scenario_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Training source contains duplicate scenario IDs")

    rng = random.Random(seed)
    pool = list(records)
    rng.shuffle(pool)
    severity_targets = _quota(Counter(str(r["ground_truth"]["baseline"]["severity"]) for r in pool), count)
    dimension_targets = {
        "difficulty": _quota(Counter(str(r["difficulty"]) for r in pool), count),
        "failure_type": _quota(Counter(str(r["failure_type"]) for r in pool), count),
        "topology": _quota(Counter(_topology(r["failure_description"]) for r in pool), count),
    }
    chosen: list[dict[str, Any]] = []
    counts = {"severity": Counter(), **{k: Counter() for k in dimension_targets}}
    for _ in range(count):
        severity_gaps = {k: target - counts["severity"][k] for k, target in severity_targets.items()}
        severity = max(severity_gaps, key=lambda k: (severity_gaps[k], -list(severity_targets).index(k)))
        candidates = [r for r in pool if r["ground_truth"]["baseline"]["severity"] == severity]
        if not candidates:
            # If a constrained group is exhausted, continue from remaining records,
            # still preferring marginal diversity gains.
            candidates = pool
        def score(row: dict[str, Any]) -> float:
            values = {"difficulty": str(row["difficulty"]), "failure_type": str(row["failure_type"]),
                      "topology": _topology(row["failure_description"])}
            total_score = 0.0
            for dim, value in values.items():
                target = dimension_targets[dim].get(value, 0)
                gap = target - counts[dim][value]
                total_score += (gap / max(1, target)) if gap > 0 else -0.2
            return total_score
        selected = max(candidates, key=score)  # Seeded shuffle supplies deterministic tie order.
        chosen.append(selected)
        counts["severity"][str(selected["ground_truth"]["baseline"]["severity"])] += 1
        for dim in dimension_targets:
            value = _topology(selected["failure_description"]) if dim == "topology" else str(selected[dim])
            counts[dim][value] += 1
        pool.remove(selected)
    return chosen


def make_prompt(record: dict[str, Any]) -> str:
    """Render one compact, consistent analyst prompt from input-only fields."""
    network = record["network"]
    scenario = {
        "failure_type": record["failure_type"],
        "failed_nodes": record["failed_nodes"],
        "failure_description": record["failure_description"],
        "nodes": [
            {key: node[key] for key in ("id", "type", "capacity", "load", "buffer_hours",
                                        "critical", "criticality_weight", "recovery_hours")}
            for node in network["nodes"]
        ],
        "edges": network["edges"],
    }
    schema = {"cascade_summary": "string", "direct_impacts": ["node_id"],
              "second_order_impacts": ["node_id"], "third_order_impacts": ["node_id"],
              "further_impacts": ["node_id"], "impacted_nodes": ["node_id"],
              "predicted_bottleneck": "node_id or null", "severity": "low|medium|high|critical",
              "ranked_mitigation_interventions": ["none|reroute|backup_supplier|prioritize"],
              "recommended_intervention": "strategy", "explanation": "string"}
    return (f"{INSTRUCTION}\n\nScenario input (JSON):\n"
            f"{json.dumps(scenario, sort_keys=True, separators=(',', ':'), allow_nan=False)}\n\n"
            f"Output JSON schema:\n{json.dumps(schema, sort_keys=True, separators=(',', ':'))}")


def make_completion(record: dict[str, Any]) -> str:
    """Serialize a compact projection of the engine-derived AI target."""
    target = record["ai_target"]
    output = {
        "cascade_summary": target["cascade_summary"],
        "direct_impacts": target["direct_impacts"],
        "second_order_impacts": target["second_order_impacts"],
        "third_order_impacts": target["third_order_impacts"],
        "further_impacts": target["further_impacts"],
        "impacted_nodes": target["structured_response"]["impacted_nodes"],
        "predicted_bottleneck": target["predicted_bottleneck"],
        "severity": target["severity"],
        "ranked_mitigation_interventions": target["ranked_mitigation_interventions"],
        "recommended_intervention": target["structured_response"]["recommended_intervention"],
        "explanation": target["explanation"],
    }
    if tuple(output) != COMPLETION_KEYS:
        raise ValueError("Completion schema order or fields changed")
    return json.dumps(output, indent=2, sort_keys=True, allow_nan=False)


def convert_record(record: dict[str, Any]) -> dict[str, str]:
    """Convert a source record into the two-column prompt/completion format."""
    if record.get("split") != "train":
        raise ValueError("Only train-split records can be converted")
    return {"prompt": make_prompt(record), "completion": make_completion(record)}


def validate_trial(rows: list[dict[str, Any]], source_records: list[dict[str, Any]],
                   selected_ids: list[str] | None = None) -> None:
    """Check count, two-column shape, JSON completions, and source-target identity."""
    if len(rows) != TRIAL_SIZE:
        raise ValueError(f"Trial must contain exactly {TRIAL_SIZE} records; found {len(rows)}")
    if any(set(row) != {"prompt", "completion"} for row in rows):
        raise ValueError("Every converted record must contain exactly prompt and completion")
    lookup = {r["scenario_id"]: r for r in source_records}
    for row in rows:
        if not row["prompt"].startswith(INSTRUCTION):
            raise ValueError("Prompt is missing the stable instruction prefix")
        target = json.loads(row["completion"])
        if set(target) != set(COMPLETION_KEYS):
            raise ValueError("Completion does not conform to the documented output schema")
    if len(lookup) < TRIAL_SIZE:
        raise ValueError("Source has fewer than 50 unique scenario IDs")
    if selected_ids is not None:
        if len(selected_ids) != TRIAL_SIZE or len(set(selected_ids)) != TRIAL_SIZE:
            raise ValueError("Metadata must list 50 unique selected scenario IDs")
        if any(sid not in lookup or lookup[sid].get("split") != "train" for sid in selected_ids):
            raise ValueError("Selected metadata IDs must all refer to training records")
        for row, sid in zip(rows, selected_ids):
            if row != convert_record(lookup[sid]):
                raise ValueError(f"Converted prompt/completion does not match source target for {sid}")


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    """Write stable UTF-8 JSONL without non-finite values."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def prepare_trial(seed: int = SELECTION_SEED) -> dict[str, Any]:
    """Create trial JSONL and safe local metadata/report from train.jsonl only."""
    source_rows = load_jsonl(TRAIN_PATH)
    if not source_rows or any(row.get("split") != "train" for row in source_rows):
        raise ValueError("Configured train.jsonl is empty or contains non-training rows")
    selected = select_trial_records(source_rows, count=TRIAL_SIZE, seed=seed)
    converted = [convert_record(row) for row in selected]
    validate_trial(converted, selected, [row["scenario_id"] for row in selected])
    write_jsonl(TRIAL_PATH, converted)
    ids = [row["scenario_id"] for row in selected]
    metadata = {
        "conversion_version": CONVERSION_VERSION,
        "selection_seed": seed,
        "source_file": "data/train.jsonl",
        "source_split": "train",
        "record_count": len(converted),
        "trial_file": "data/adaption_trial/ripple_trial_50.jsonl",
        "selected_scenario_ids": ids,
        "selection_distribution": {
            "severity": dict(Counter(r["ground_truth"]["baseline"]["severity"] for r in selected)),
            "difficulty": dict(Counter(r["difficulty"] for r in selected)),
            "failure_type": dict(Counter(r["failure_type"] for r in selected)),
            "topology": dict(Counter(_topology(r["failure_description"]) for r in selected)),
        },
        "trial_sha256": hashlib.sha256(TRIAL_PATH.read_bytes()).hexdigest(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SELECTION_SEED)
    parser.add_argument("--upload", action="store_true", help="Explicitly upload only the 50-row trial file")
    parser.add_argument("--estimate", action="store_true", help="Explicitly request estimate-only Adaptive Data pricing")
    parser.add_argument("--dataset-id", help="Reuse the dataset ID saved by a prior successful trial upload for estimate-only")
    args = parser.parse_args()
    metadata = prepare_trial(args.seed)
    from data.adaption_trial.adaption_trial_client import local_report, run_api_actions, save_safe_report
    report = local_report(metadata)
    if args.dataset_id and (args.upload or not args.estimate):
        parser.error("--dataset-id is only valid with --estimate and without --upload")
    if args.upload or args.estimate:
        report.update(run_api_actions(upload=args.upload, estimate=args.estimate, dataset_id=args.dataset_id))
    save_safe_report(report)
    print(json.dumps({"mode": "upload_and_estimate" if args.upload and args.estimate else "upload" if args.upload else "estimate_only" if args.estimate else "local_only",
                      "rows": metadata["record_count"], "trial_file": metadata["trial_file"],
                      "api_key_configured": report["api_key_configured"],
                      "dataset_id": report.get("dataset_id"),
                      "upload_status": report.get("upload_status", "not_attempted"),
                      "ingestion_status": report.get("ingestion_status"),
                      "ingested_row_count": report.get("ingested_row_count"),
                      "column_mapping": report.get("column_mapping"),
                      "column_mapping_verified": report.get("column_mapping_verified", False),
                      "estimate_requested": report.get("estimate_requested", False),
                      "estimate_status": report.get("estimate_status"),
                      "estimated_credits": report.get("estimated_credits"),
                      "estimated_minutes": report.get("estimated_minutes"),
                      "request_configuration": report.get("request_configuration")}, indent=2))


if __name__ == "__main__":
    _main()
