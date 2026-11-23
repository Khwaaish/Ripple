"""Evaluate JSON predictions against Ripple's engine-labeled held-out test set.

This module contains no model inference or Adaption client. A future predictor can
implement :class:`Predictor`; current evaluations can load saved JSONL predictions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Protocol

from data.adaption_trial.prepare_trial import COMPLETION_KEYS
from data.validate_dataset import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_PATH = ROOT / "data" / "test.jsonl"
DEFAULT_REPORT_PATH = ROOT / "data" / "evaluation" / "evaluation_report.json"
SEVERITIES = {"low", "medium", "high", "critical"}
STRATEGIES = {"none", "reroute", "backup_supplier", "prioritize"}
STRING_ARRAY_KEYS = (
    "direct_impacts", "second_order_impacts", "third_order_impacts",
    "further_impacts", "impacted_nodes", "ranked_mitigation_interventions",
)
STRUCTURED_KEYS = (
    "direct_impacts", "second_order_impacts", "third_order_impacts",
    "further_impacts", "impacted_nodes", "predicted_bottleneck", "severity",
    "ranked_mitigation_interventions", "recommended_intervention",
)


class Predictor(Protocol):
    """Interface for genuine model inference; not implemented by this package."""

    def predict(self, prompt: str) -> str:
        """Return the model's raw response for one prompt."""


@dataclass(frozen=True)
class ParsedPrediction:
    value: dict[str, Any] | None
    error: str | None
    json_valid: bool = False


def parse_prediction(raw: Any) -> ParsedPrediction:
    """Safely parse and validate one raw JSON completion without coercion."""
    if not isinstance(raw, str) or not raw.strip():
        return ParsedPrediction(None, "prediction must be a non-empty JSON string")
    try:
        value = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (json.JSONDecodeError, ValueError):
        return ParsedPrediction(None, "prediction is not valid strict JSON")
    if not isinstance(value, dict):
        return ParsedPrediction(None, "prediction JSON must be an object")
    missing = set(COMPLETION_KEYS) - set(value)
    if missing:
        return ParsedPrediction(None, "prediction is missing required fields", True)
    if (not isinstance(value["cascade_summary"], str)
            or not isinstance(value["explanation"], str)
            or any(not isinstance(value[key], list) or not all(isinstance(item, str) for item in value[key])
                   for key in STRING_ARRAY_KEYS)
            or (value["predicted_bottleneck"] is not None and not isinstance(value["predicted_bottleneck"], str))
            or not isinstance(value["severity"], str) or value["severity"] not in SEVERITIES
            or not isinstance(value["recommended_intervention"], str) or value["recommended_intervention"] not in STRATEGIES):
        return ParsedPrediction(None, "prediction contains invalid required-field types or values", True)
    ranking = value["ranked_mitigation_interventions"]
    if len(ranking) != len(STRATEGIES) or set(ranking) != STRATEGIES:
        return ParsedPrediction(None, "prediction intervention ranking must contain each supported strategy once", True)
    return ParsedPrediction(value, None, True)


def _read_predictions(path: Path) -> tuple[dict[str, ParsedPrediction], dict[str, int]]:
    """Read scenario_id/raw-response rows; duplicates invalidate that scenario."""
    predictions: dict[str, ParsedPrediction] = {}
    counts = Counter()
    seen: set[str] = set()
    duplicate_ids: set[str] = set()
    try:
        stream = path.open(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read predictions file: {exc}") from exc
    with stream:
        for line_no, line in enumerate(stream, 1):
            counts["prediction_records"] += 1
            try:
                row = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            except (json.JSONDecodeError, ValueError):
                counts["malformed_prediction_records"] += 1
                continue
            if not isinstance(row, dict) or not isinstance(row.get("scenario_id"), str) or not row["scenario_id"].strip():
                counts["malformed_prediction_records"] += 1
                continue
            scenario_id = row["scenario_id"]
            if scenario_id in seen:
                duplicate_ids.add(scenario_id)
                counts["duplicate_prediction_records"] += 1
                continue
            seen.add(scenario_id)
            parsed = parse_prediction(row.get("prediction"))
            predictions[scenario_id] = parsed
            if parsed.error:
                counts["malformed_prediction_records"] += 1
    for scenario_id in duplicate_ids:
        predictions[scenario_id] = ParsedPrediction(None, "duplicate scenario_id makes prediction ambiguous")
    return predictions, dict(counts)


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _set_scores(predicted: set[str], expected: set[str]) -> tuple[float, float, float, float]:
    intersection = len(predicted & expected)
    precision = intersection / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = intersection / len(expected) if expected else (1.0 if not predicted else 0.0)
    f1 = _f1(precision, recall)
    union = predicted | expected
    jaccard = len(predicted & expected) / len(union) if union else 1.0
    return precision, recall, f1, jaccard


def _metric(value: float | None, denominator: int, *, note: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"value": round(value, 6) if value is not None else None, "denominator": denominator}
    if note:
        result["note"] = note
    return result


def evaluate_predictions(
    test_path: Path = DEFAULT_TEST_PATH,
    predictions_path: Path | None = None,
    *,
    model_id: str | None = None,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Compare predictions with test ground truth and return an aggregate-only report."""
    if predictions_path is None:
        raise ValueError("A JSONL prediction file is required; model inference is not configured")
    test_rows, read_errors = read_jsonl(test_path)
    if read_errors:
        raise ValueError("Held-out test file is not valid JSONL")
    if any(row.get("split") != "test" for row in test_rows):
        raise ValueError("Evaluation input must contain only split='test' records")
    ids = [row.get("scenario_id") for row in test_rows]
    if any(not isinstance(sid, str) or not sid for sid in ids) or len(ids) != len(set(ids)):
        raise ValueError("Held-out test records must have unique non-empty scenario IDs")

    predictions, file_counts = _read_predictions(predictions_path)
    expected_ids = set(ids)
    unexpected = set(predictions) - expected_ids
    counts = Counter(file_counts)
    counts["unexpected_prediction_scenarios"] = len(unexpected)
    counts["missing_predictions"] = len(expected_ids - set(predictions))

    valid_json = sum(item.json_valid for scenario_id, item in predictions.items() if scenario_id in expected_ids)
    valid: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in test_rows:
        parsed = predictions.get(row["scenario_id"])
        if parsed and parsed.value is not None:
            valid.append((parsed.value, row["ground_truth"]))
    successful = len(valid)
    total = len(test_rows)
    counts["successful_predictions"] = successful
    counts["malformed_or_incomplete_predictions"] = max(0, total - successful - counts["missing_predictions"])
    counts["valid_json_predictions"] = valid_json

    severity_correct = 0
    bottleneck_correct = 0
    recommended_correct = 0
    ranking_exact = 0
    structured_exact = 0
    direct_scores: list[tuple[float, float, float]] = []
    downstream_scores: list[tuple[float, float, float]] = []
    overlap_scores: list[float] = []
    for prediction, truth in valid:
        baseline = truth["baseline"]
        severity_correct += prediction["severity"] == baseline["severity"]
        bottleneck_correct += prediction["predicted_bottleneck"] == baseline["bottleneck_node"]
        expected_ranking = truth["recommendation_ranking"]
        recommended_correct += prediction["recommended_intervention"] == truth["recommended_strategy"]
        ranking_exact += prediction["ranked_mitigation_interventions"] == expected_ranking
        structured_exact += all(
            (prediction[key] == truth["recommended_strategy"] if key == "recommended_intervention"
             else prediction[key] == expected_ranking if key == "ranked_mitigation_interventions"
             else prediction[key] == baseline["bottleneck_node"] if key == "predicted_bottleneck"
             else prediction[key] == baseline["severity"] if key == "severity"
             else prediction[key] == baseline[
                 {"direct_impacts": "direct_impacts", "second_order_impacts": "second_order_impacts",
                  "third_order_impacts": "third_order_impacts", "further_impacts": "further_impacts",
                  "impacted_nodes": "impacted_nodes"}[key]
             ]) for key in STRUCTURED_KEYS
        )
        direct_scores.append(_set_scores(set(prediction["direct_impacts"]), set(baseline["direct_impacts"]))[:3])
        expected_downstream = set(baseline["second_order_impacts"] + baseline["third_order_impacts"] + baseline["further_impacts"])
        predicted_downstream = set(prediction["second_order_impacts"] + prediction["third_order_impacts"] + prediction["further_impacts"])
        downstream_scores.append(_set_scores(predicted_downstream, expected_downstream)[:3])
        overlap_scores.append(_set_scores(set(prediction["impacted_nodes"]), set(baseline["impacted_nodes"]))[3])

    def averaged(index: int, values: list[tuple[float, float, float]]) -> float | None:
        return sum(value[index] for value in values) / len(values) if values else None

    metrics: dict[str, Any] = {
        "json_validity_rate": _metric(valid_json / total if total else None, total),
        "required_field_completeness_rate": _metric(successful / total if total else None, total),
        "severity_accuracy": _metric(severity_correct / successful if successful else None, successful),
        "direct_impact_precision_macro": _metric(averaged(0, direct_scores), successful),
        "direct_impact_recall_macro": _metric(averaged(1, direct_scores), successful),
        "direct_impact_f1_macro": _metric(averaged(2, direct_scores), successful),
        "downstream_impact_precision_macro": _metric(averaged(0, downstream_scores), successful),
        "downstream_impact_recall_macro": _metric(averaged(1, downstream_scores), successful),
        "downstream_impact_f1_macro": _metric(averaged(2, downstream_scores), successful),
        "affected_node_jaccard_macro": _metric(sum(overlap_scores) / len(overlap_scores) if overlap_scores else None, successful),
        "bottleneck_accuracy": _metric(bottleneck_correct / successful if successful else None, successful),
        "recommended_intervention_agreement": _metric(recommended_correct / successful if successful else None, successful),
        "intervention_ranking_exact_agreement": _metric(ranking_exact / successful if successful else None, successful),
        "structured_exact_match_rate": _metric(structured_exact / successful if successful else None, successful),
        "impact_score_mae": _metric(None, 0, note="Unavailable: impact_score is not part of the trained completion schema."),
        "impact_score_rmse": _metric(None, 0, note="Unavailable: impact_score is not part of the trained completion schema."),
    }
    timestamp = evaluated_at or datetime.now(timezone.utc)
    warnings = []
    if successful < total:
        warnings.append("Evaluation coverage is incomplete; aggregate accuracy metrics use successful predictions only.")
    if unexpected:
        warnings.append("Prediction file contains scenario IDs not present in the held-out test split; they were excluded.")
    return {
        "report_version": "1.0",
        "evaluation_timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model_id": model_id,
        "model_inference_performed": False,
        "prediction_source": str(predictions_path),
        "test_source": "data/test.jsonl",
        "test_samples_evaluated": total,
        "successful_predictions": successful,
        "malformed_or_incomplete_predictions": counts["malformed_or_incomplete_predictions"],
        "missing_predictions": counts["missing_predictions"],
        "malformed_prediction_records": counts["malformed_prediction_records"],
        "duplicate_prediction_records": counts["duplicate_prediction_records"],
        "unexpected_prediction_scenarios": counts["unexpected_prediction_scenarios"],
        "metrics": metrics,
        "metric_definitions": {
            "json_validity_rate": "Predictions that parse as strict JSON objects divided by test samples; missing rows count as invalid.",
            "required_field_completeness_rate": "Predictions satisfying every required completion key and type divided by all test samples.",
            "severity_accuracy": "Exact severity label agreement among complete valid predictions.",
            "direct_impact_*_macro": "Per-scenario set precision, recall, or F1 for direct_impacts, averaged equally; empty/empty scores 1.",
            "downstream_impact_*_macro": "Per-scenario set precision, recall, or F1 over the union of second-, third-, and further-order nodes, averaged equally; empty/empty scores 1.",
            "affected_node_jaccard_macro": "Mean Jaccard overlap of predicted and ground-truth impacted_nodes; empty/empty scores 1.",
            "bottleneck_accuracy": "Exact predicted_bottleneck match, including null, among complete valid predictions.",
            "recommended_intervention_agreement": "Exact recommended strategy agreement among complete valid predictions.",
            "intervention_ranking_exact_agreement": "Exact ordered ranking agreement for all supported strategies.",
            "structured_exact_match_rate": "Exact agreement on impact layers, impacted nodes, bottleneck, severity, complete intervention ranking, and recommendation; prose is excluded.",
            "impact_score_mae_rmse": "Not computed because impact_score is absent from the model's trained completion schema.",
            "averaging": "Classification and set metrics are macro-averaged per successfully parsed, complete prediction; coverage rates use all test samples.",
        },
        "warnings": warnings,
    }


def write_report(report: dict[str, Any], output_path: Path = DEFAULT_REPORT_PATH) -> None:
    """Write aggregate metrics only; the report never includes individual labels."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST_PATH)
    parser.add_argument("--predictions", type=Path, required=True,
                        help="JSONL rows with scenario_id and prediction (raw JSON response string)")
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    report = evaluate_predictions(args.test, args.predictions, model_id=args.model_id)
    write_report(report, args.report)
    print(json.dumps({key: value for key, value in report.items() if key != "metric_definitions"}, indent=2))


if __name__ == "__main__":
    _main()
