"""Build local JSONL scenario datasets from deterministic engine outputs."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time
from typing import Any

from engine.interventions import compare_interventions
from engine.scenario_generator import generate_scenario
from engine.simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SEED_START = 100_000
TEST_SEED_START = 900_000
INTERVENTIONS = ("none", "reroute", "backup_supplier", "prioritize")


def build_record(seed: int, split: str) -> dict[str, Any]:
    """Create one complete record; all outcome labels come from the engine."""
    scenario = generate_scenario(seed, split)
    baseline = simulate(scenario.network, scenario.failed_nodes, intervention="none")
    comparison = compare_interventions(scenario.network, scenario.failed_nodes)
    base = baseline.to_dict()
    comparison_data = comparison.to_dict()
    base_outcome = {
        "cascade_impacts_by_round": {
            f"round_{snapshot['round']}": snapshot["newly_impacted"]
            for snapshot in base["round_snapshots"]
        },
        "direct_impacts": base["directly_impacted_nodes"],
        "second_order_impacts": base["second_order_impacted_nodes"],
        "third_order_impacts": base["third_order_impacted_nodes"],
        "further_impacts": base["further_impacted_nodes"],
        "impacted_nodes": base["all_impacted_nodes"],
        "node_impacts": base["node_impacts"],
        "overloaded_nodes": base["overloaded_nodes"],
        "critical_shortages": base["critical_shortage_nodes"],
        "bottleneck_node": base["bottleneck_node"],
        "first_stockout_time_h": base["first_predicted_stockout_time_h"],
        "propagation_rounds": base["propagation_rounds"],
        "impact_score": base["impact_score"],
        "severity": base["severity"],
        "estimated_recovery_time_h": base["recovery_estimate_h"],
        "round_snapshots": base["round_snapshots"],
        "reasoning": base["reasoning"],
    }
    intervention_results = comparison_data["scenarios"]
    for result in intervention_results.values():
        score = result["impact_score"]
        result["relative_improvement_vs_baseline"] = (
            round((base["impact_score"] - score) / base["impact_score"], 6)
            if base["impact_score"] else (0.0 if score == 0 else None)
        )
    ranking = comparison_data["ranking"]
    target = {
        "cascade_summary": _cascade_summary(base),
        "direct_impacts": base_outcome["direct_impacts"],
        "second_order_impacts": base_outcome["second_order_impacts"],
        "third_order_impacts": base_outcome["third_order_impacts"],
        "further_impacts": base_outcome["further_impacts"],
        "predicted_bottleneck": base_outcome["bottleneck_node"],
        "severity": base_outcome["severity"],
        "ranked_mitigation_interventions": ranking,
        "explanation": _explanation(base, ranking, comparison_data["recommendation_reason"]),
        "structured_response": {
            "summary": _cascade_summary(base),
            "impacted_nodes": base["all_impacted_nodes"],
            "bottleneck": base["bottleneck_node"],
            "severity": base["severity"],
            "recommended_intervention": comparison_data["recommended_strategy"],
            "intervention_ranking": ranking,
        },
    }
    return {
        **scenario.to_metadata(f"{split}-{seed:08d}", split),
        "ground_truth": {"baseline": base_outcome, "interventions": intervention_results,
                         "recommendation_ranking": ranking,
                         "recommended_strategy": comparison_data["recommended_strategy"],
                         "recommendation_reason": comparison_data["recommendation_reason"]},
        "ai_target": target,
    }


def _cascade_summary(result: dict[str, Any]) -> str:
    impacts = result["all_impacted_nodes"]
    if not impacts:
        return f"No downstream nodes experience a modeled supply shortage; severity is {result['severity']}."
    rounds = result["propagation_rounds"]
    bottleneck = result["bottleneck_node"] or "none"
    return (f"{len(impacts)} downstream node(s) experience modeled shortages across "
            f"{rounds} propagation round(s); bottleneck {bottleneck}; severity {result['severity']}; "
            f"weighted impact score {result['impact_score']:.6f}.")


def _explanation(result: dict[str, Any], ranking: list[str], reason: str) -> str:
    return (f"The engine found {len(result['all_impacted_nodes'])} impacted downstream node(s), "
            f"with {len(result['critical_shortage_nodes'])} critical shortage(s). {reason} "
            f"Ranking: {' > '.join(ranking)}.")


def generate_splits(train_count: int = 2000, test_count: int = 300,
                    train_seed_start: int = TRAIN_SEED_START,
                    test_seed_start: int = TEST_SEED_START) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate independently seeded and disjoint train/test records."""
    if train_count < 0 or test_count < 0:
        raise ValueError("Dataset counts must be non-negative")
    train_seeds = range(train_seed_start, train_seed_start + train_count)
    test_seeds = range(test_seed_start, test_seed_start + test_count)
    if set(train_seeds).intersection(test_seeds):
        raise ValueError("Train and test seed ranges overlap")
    train = [build_record(seed, "train") for seed in train_seeds]
    test = [build_record(seed, "test") for seed in test_seeds]
    return train, test


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write deterministic UTF-8 JSONL directly to the requested path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-count", type=int, default=2000)
    parser.add_argument("--test-count", type=int, default=300)
    parser.add_argument("--train-seed-start", type=int, default=TRAIN_SEED_START)
    parser.add_argument("--test-seed-start", type=int, default=TEST_SEED_START)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    start = time.perf_counter()
    train, test = generate_splits(args.train_count, args.test_count, args.train_seed_start, args.test_seed_start)
    write_jsonl(args.output_dir / "train.jsonl", train)
    write_jsonl(args.output_dir / "test.jsonl", test)
    print(json.dumps({"train": len(train), "test": len(test), "elapsed_seconds": round(time.perf_counter() - start, 3)}))


if __name__ == "__main__":
    _main()
