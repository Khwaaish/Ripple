"""Validate JSONL dataset schema, splits, duplicates, and engine-derived labels."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from engine.interventions import compare_interventions
from engine.models import SupplyNetwork
from engine.simulate import simulate
from data.generate_dataset import INTERVENTIONS, ROOT, _cascade_summary, _explanation

SEVERITIES = ("low", "medium", "high", "critical")
DIFFICULTIES = ("easy", "medium", "hard")
REQUIRED_TOP = {"scenario_id", "seed", "split", "difficulty", "network", "failed_nodes",
                "failure_type", "failure_description", "ground_truth", "ai_target"}
REQUIRED_BASELINE = {"cascade_impacts_by_round", "direct_impacts", "second_order_impacts",
                     "third_order_impacts", "further_impacts", "impacted_nodes", "node_impacts",
                     "overloaded_nodes", "critical_shortages", "bottleneck_node", "first_stockout_time_h",
                     "propagation_rounds", "impact_score", "severity", "estimated_recovery_time_h",
                     "round_snapshots", "reasoning"}


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read JSONL, reporting malformed lines without stopping the file scan."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        stream = path.open(encoding="utf-8")
    except OSError as exc:
        return rows, [f"{path}: {exc}"]
    with stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                errors.append(f"{path}:{line_no}: blank lines are not valid JSONL records")
                continue
            try:
                value = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"invalid numeric constant {token}")))
                if not isinstance(value, dict):
                    raise ValueError("record must be a JSON object")
                rows.append(value)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"{path}:{line_no}: {exc}")
    return rows, errors


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _baseline_projection(result: Any) -> dict[str, Any]:
    data = result.to_dict()
    return {
        "cascade_impacts_by_round": {f"round_{x['round']}": x["newly_impacted"] for x in data["round_snapshots"]},
        "direct_impacts": data["directly_impacted_nodes"],
        "second_order_impacts": data["second_order_impacted_nodes"],
        "third_order_impacts": data["third_order_impacted_nodes"],
        "further_impacts": data["further_impacted_nodes"],
        "impacted_nodes": data["all_impacted_nodes"],
        "node_impacts": data["node_impacts"],
        "overloaded_nodes": data["overloaded_nodes"],
        "critical_shortages": data["critical_shortage_nodes"],
        "bottleneck_node": data["bottleneck_node"],
        "first_stockout_time_h": data["first_predicted_stockout_time_h"],
        "propagation_rounds": data["propagation_rounds"],
        "impact_score": data["impact_score"],
        "severity": data["severity"],
        "estimated_recovery_time_h": data["recovery_estimate_h"],
        "round_snapshots": data["round_snapshots"],
        "reasoning": data["reasoning"],
    }


def _add(errors: list[str], scenario_id: str, message: str) -> None:
    errors.append(f"{scenario_id}: {message}")


def validate_record(row: dict[str, Any], expected_split: str, errors: list[str]) -> tuple[str, int, str]:
    """Validate a record and recompute its engine labels; return ID, size, duplicate hash."""
    sid = str(row.get("scenario_id", "<missing-id>"))
    missing = REQUIRED_TOP - row.keys()
    if missing:
        _add(errors, sid, f"missing top-level keys: {sorted(missing)}")
        return sid, 0, ""
    if row["split"] != expected_split:
        _add(errors, sid, f"split is {row['split']!r}, expected {expected_split!r}")
    if not isinstance(row["seed"], int) or isinstance(row["seed"], bool):
        _add(errors, sid, "seed must be an integer")
    if row["difficulty"] not in DIFFICULTIES:
        _add(errors, sid, f"invalid difficulty {row['difficulty']!r}")
    if row["failure_type"] not in {"supplier", "warehouse", "store", "multiple"}:
        _add(errors, sid, f"invalid failure_type {row['failure_type']!r}")
    if not _finite(row):
        _add(errors, sid, "record contains a non-finite numeric value")
    try:
        network = SupplyNetwork.from_dict(row["network"])
        failed = row["failed_nodes"]
        if not isinstance(failed, list) or not failed or not all(isinstance(x, str) for x in failed):
            raise ValueError("failed_nodes must be a non-empty list of strings")
        missing_nodes = set(failed) - network.nodes.keys()
        if missing_nodes:
            raise ValueError(f"failed node IDs do not exist: {sorted(missing_nodes)}")
    except (TypeError, ValueError, KeyError) as exc:
        _add(errors, sid, f"invalid network/failure data: {exc}")
        return sid, 0, ""

    ground = row["ground_truth"]
    if not isinstance(ground, dict) or not isinstance(ground.get("baseline"), dict):
        _add(errors, sid, "ground_truth.baseline must be an object")
        return sid, len(network.nodes), ""
    base = ground["baseline"]
    missing_base = REQUIRED_BASELINE - base.keys()
    if missing_base:
        _add(errors, sid, f"missing baseline keys: {sorted(missing_base)}")
    if base.get("severity") not in SEVERITIES:
        _add(errors, sid, f"invalid severity {base.get('severity')!r}")
    intervention_results = ground.get("interventions")
    if not isinstance(intervention_results, dict) or set(intervention_results) != set(INTERVENTIONS):
        _add(errors, sid, "all four intervention outputs must be present")
    if not isinstance(row["ai_target"], dict):
        _add(errors, sid, "ai_target must be an object")

    try:
        expected_base = _baseline_projection(simulate(network, failed, "none"))
        if base != expected_base:
            _add(errors, sid, "baseline labels do not match a fresh engine simulation")
        comparison = compare_interventions(network, failed).to_dict()
        for result in comparison["scenarios"].values():
            score = result["impact_score"]
            result["relative_improvement_vs_baseline"] = (
                round((expected_base["impact_score"] - score) / expected_base["impact_score"], 6)
                if expected_base["impact_score"] else (0.0 if score == 0 else None)
            )
        if intervention_results != comparison["scenarios"]:
            _add(errors, sid, "intervention labels do not match fresh engine comparison")
        for key, value in (("recommendation_ranking", comparison["ranking"]),
                           ("recommended_strategy", comparison["recommended_strategy"]),
                           ("recommendation_reason", comparison["recommendation_reason"])):
            if ground.get(key) != value:
                _add(errors, sid, f"ground_truth.{key} differs from engine comparison")
        target = row["ai_target"] if isinstance(row["ai_target"], dict) else {}
        wanted_target = {
            "cascade_summary": _cascade_summary({
                "all_impacted_nodes": expected_base["impacted_nodes"],
                "propagation_rounds": expected_base["propagation_rounds"],
                "bottleneck_node": expected_base["bottleneck_node"],
                "severity": expected_base["severity"],
                "impact_score": expected_base["impact_score"],
            }),
            "explanation": _explanation({
                "all_impacted_nodes": expected_base["impacted_nodes"],
                "critical_shortage_nodes": expected_base["critical_shortages"],
            }, comparison["ranking"], comparison["recommendation_reason"]),
            "direct_impacts": expected_base["direct_impacts"],
            "second_order_impacts": expected_base["second_order_impacts"],
            "third_order_impacts": expected_base["third_order_impacts"],
            "further_impacts": expected_base["further_impacts"],
            "predicted_bottleneck": expected_base["bottleneck_node"],
            "severity": expected_base["severity"],
            "ranked_mitigation_interventions": comparison["ranking"],
            "structured_response": {
                "summary": target.get("cascade_summary"),
                "impacted_nodes": expected_base["impacted_nodes"],
                "bottleneck": expected_base["bottleneck_node"],
                "severity": expected_base["severity"],
                "recommended_intervention": comparison["recommended_strategy"],
                "intervention_ranking": comparison["ranking"],
            },
        }
        required_targets = {"cascade_summary", "direct_impacts", "second_order_impacts", "third_order_impacts",
                            "further_impacts", "predicted_bottleneck", "severity", "ranked_mitigation_interventions",
                            "explanation", "structured_response"}
        if required_targets - target.keys():
            _add(errors, sid, f"missing AI target keys: {sorted(required_targets - target.keys())}")
        for key, value in wanted_target.items():
            if target.get(key) != value:
                _add(errors, sid, f"AI target field {key!r} contradicts engine output")
        if not isinstance(target.get("cascade_summary"), str) or not isinstance(target.get("explanation"), str):
            _add(errors, sid, "AI target must include textual summary and explanation")
    except (ValueError, KeyError, TypeError) as exc:
        _add(errors, sid, f"engine recomputation failed: {exc}")

    canonical = json.dumps({"network": row["network"], "failed_nodes": sorted(failed)}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sid, len(network.nodes), hashlib.sha256(canonical.encode()).hexdigest()


def validate_dataset(train_path: Path, test_path: Path, *, expected_train: int = 2000,
                     expected_test: int = 300) -> dict[str, Any]:
    """Validate both splits and return a JSON-serializable quality report."""
    train, errors = read_jsonl(train_path)
    test, read_errors = read_jsonl(test_path)
    errors.extend(read_errors)
    severity_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    size_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    all_ids: list[str] = []
    fingerprints: list[str] = []
    for split, rows in (("train", train), ("test", test)):
        for row in rows:
            sid, size, fingerprint = validate_record(row, split, errors)
            all_ids.append(sid)
            fingerprints.append(fingerprint)
            severity_counts[str(row.get("ground_truth", {}).get("baseline", {}).get("severity", "invalid"))] += 1
            difficulty_counts[str(row.get("difficulty", "invalid"))] += 1
            if size:
                size_counts[str(size)] += 1
            failure_counts[str(row.get("failure_type", "invalid"))] += 1
    id_counts = Counter(all_ids)
    duplicate_ids = sum(count - 1 for count in id_counts.values() if count > 1)
    overlap = set(r.get("scenario_id") for r in train) & set(r.get("scenario_id") for r in test)
    fingerprint_counts = Counter(x for x in fingerprints if x)
    duplicate_scenarios = sum(count - 1 for count in fingerprint_counts.values() if count > 1)
    if len(train) != expected_train:
        errors.append(f"train row count {len(train)} != expected {expected_train}")
    if len(test) != expected_test:
        errors.append(f"test row count {len(test)} != expected {expected_test}")
    if duplicate_ids:
        errors.append(f"found {duplicate_ids} duplicate scenario IDs")
    if overlap:
        errors.append(f"found {len(overlap)} train/test ID leaks")
    if duplicate_scenarios:
        errors.append(f"found {duplicate_scenarios} duplicate network/failure scenarios")
    warnings: list[str] = []
    total = len(train) + len(test)
    if total and any(severity_counts[level] == 0 for level in SEVERITIES):
        warnings.append("At least one engine-derived severity category is absent; inspect generator outcome diversity.")
    for label, counts in (("severity", severity_counts), ("difficulty", difficulty_counts), ("failure type", failure_counts)):
        if total and counts and max(counts.values()) / total > .8:
            warnings.append(f"{label} distribution is highly concentrated in {max(counts, key=counts.get)}.")
    if set(size_counts) != {str(n) for n in range(6, 13)}:
        warnings.append("Network size distribution does not cover every size from 6 through 12 nodes.")
    report = {
        "total_scenarios": total,
        "split_counts": {"train": len(train), "test": len(test)},
        "severity_distribution": {k: severity_counts[k] for k in (*SEVERITIES, "invalid") if severity_counts[k]},
        "difficulty_distribution": {k: difficulty_counts[k] for k in (*DIFFICULTIES, "invalid") if difficulty_counts[k]},
        "network_size_distribution": dict(sorted(size_counts.items(), key=lambda x: int(x[0]))),
        "failure_type_distribution": dict(sorted(failure_counts.items())),
        "duplicate_ids": duplicate_ids,
        "train_test_id_leaks": len(overlap),
        "duplicate_scenarios": duplicate_scenarios,
        "schema_validation_failure_count": len(errors),
        "schema_validation_failures": errors[:100],
        "warnings": warnings,
        "duplicate_definition": "SHA-256 of canonical serialized network plus sorted failed node IDs; metadata and labels excluded.",
        "held_out_test_policy": "test.jsonl is validated in place and is not used to tune generation or upload to Adaption.",
    }
    return report


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=ROOT / "data" / "train.jsonl")
    parser.add_argument("--test", type=Path, default=ROOT / "data" / "test.jsonl")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "dataset_quality_report.json")
    parser.add_argument("--expected-train", type=int, default=2000)
    parser.add_argument("--expected-test", type=int, default=300)
    args = parser.parse_args()
    report = validate_dataset(args.train, args.test, expected_train=args.expected_train, expected_test=args.expected_test)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"schema_validation_failures"}}, indent=2))
    if report["schema_validation_failure_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    _main()
