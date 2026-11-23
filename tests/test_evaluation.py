from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from data.evaluation import evaluate_predictions, parse_prediction, write_report


def _record(scenario_id: str = "test-1") -> dict:
    return {
        "scenario_id": scenario_id,
        "split": "test",
        "ground_truth": {
            "baseline": {
                "severity": "high",
                "direct_impacts": ["WH1"],
                "second_order_impacts": ["ST1"],
                "third_order_impacts": [],
                "further_impacts": [],
                "impacted_nodes": ["WH1", "ST1"],
                "bottleneck_node": "WH1",
            },
            "recommendation_ranking": ["reroute", "prioritize", "backup_supplier", "none"],
            "recommended_strategy": "reroute",
        },
    }


def _prediction(**overrides: object) -> dict:
    value = {
        "cascade_summary": "private held-out summary",
        "direct_impacts": ["WH1"],
        "second_order_impacts": ["ST1"],
        "third_order_impacts": [],
        "further_impacts": [],
        "impacted_nodes": ["WH1", "ST1"],
        "predicted_bottleneck": "WH1",
        "severity": "high",
        "ranked_mitigation_interventions": ["reroute", "prioritize", "backup_supplier", "none"],
        "recommended_intervention": "reroute",
        "explanation": "private held-out explanation",
    }
    value.update(overrides)
    return value


def _write_test_data(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "test.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_predictions(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "predictions.jsonl"
    path.write_text("".join(row + "\n" for row in rows), encoding="utf-8")
    return path


def _prediction_row(scenario_id: str, prediction: object) -> str:
    return json.dumps({"scenario_id": scenario_id, "prediction": json.dumps(prediction) if not isinstance(prediction, str) else prediction})


def test_valid_prediction_scores_all_supported_metrics(tmp_path: Path) -> None:
    test_path = _write_test_data(tmp_path, [_record()])
    predictions_path = _write_predictions(tmp_path, [_prediction_row("test-1", _prediction())])

    report = evaluate_predictions(test_path, predictions_path, model_id="local-captured-output",
                                  evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    repeated = evaluate_predictions(test_path, predictions_path, model_id="local-captured-output",
                                    evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert report == repeated
    assert report["test_samples_evaluated"] == report["successful_predictions"] == 1
    assert report["model_inference_performed"] is False
    assert report["model_id"] == "local-captured-output"
    assert report["metrics"]["severity_accuracy"]["value"] == 1
    assert report["metrics"]["direct_impact_f1_macro"]["value"] == 1
    assert report["metrics"]["downstream_impact_f1_macro"]["value"] == 1
    assert report["metrics"]["affected_node_jaccard_macro"]["value"] == 1
    assert report["metrics"]["bottleneck_accuracy"]["value"] == 1
    assert report["metrics"]["recommended_intervention_agreement"]["value"] == 1
    assert report["metrics"]["intervention_ranking_exact_agreement"]["value"] == 1
    assert report["metrics"]["impact_score_mae"]["value"] is None


def test_malformed_json_and_missing_required_field_are_not_scored(tmp_path: Path) -> None:
    assert parse_prediction("{broken").value is None
    assert parse_prediction(json.dumps({"severity": "high"})).error == "prediction is missing required fields"
    test_path = _write_test_data(tmp_path, [_record("test-1"), _record("test-2")])
    predictions_path = _write_predictions(tmp_path, [
        _prediction_row("test-1", "{broken"),
        _prediction_row("test-2", {"severity": "high"}),
    ])

    report = evaluate_predictions(test_path, predictions_path)

    assert report["successful_predictions"] == 0
    assert report["malformed_or_incomplete_predictions"] == 2
    assert report["malformed_prediction_records"] == 2
    assert report["metrics"]["severity_accuracy"]["value"] is None
    assert report["metrics"]["required_field_completeness_rate"]["value"] == 0


def test_severity_and_node_set_errors_are_measured(tmp_path: Path) -> None:
    test_path = _write_test_data(tmp_path, [_record()])
    predictions_path = _write_predictions(tmp_path, [
        _prediction_row("test-1", _prediction(severity="low", direct_impacts=["WH2"], impacted_nodes=["WH2"]))
    ])

    metrics = evaluate_predictions(test_path, predictions_path)["metrics"]

    assert metrics["severity_accuracy"]["value"] == 0
    assert metrics["direct_impact_precision_macro"]["value"] == 0
    assert metrics["direct_impact_recall_macro"]["value"] == 0
    assert metrics["affected_node_jaccard_macro"]["value"] == 0
    assert metrics["structured_exact_match_rate"]["value"] == 0


def test_empty_and_missing_predictions_report_zero_coverage(tmp_path: Path) -> None:
    test_path = _write_test_data(tmp_path, [_record("test-1"), _record("test-2")])
    predictions_path = _write_predictions(tmp_path, [])

    report = evaluate_predictions(test_path, predictions_path)

    assert report["test_samples_evaluated"] == 2
    assert report["missing_predictions"] == 2
    assert report["successful_predictions"] == 0
    assert report["warnings"]
    assert report["metrics"]["json_validity_rate"]["value"] == 0


def test_duplicate_predictions_invalidate_scenario_and_report_is_aggregate_only(tmp_path: Path) -> None:
    test_path = _write_test_data(tmp_path, [_record()])
    encoded = _prediction_row("test-1", _prediction())
    predictions_path = _write_predictions(tmp_path, [encoded, encoded])
    report = evaluate_predictions(test_path, predictions_path)
    output = tmp_path / "evaluation_report.json"

    write_report(report, output)

    saved = output.read_text(encoding="utf-8")
    assert report["duplicate_prediction_records"] == 1
    assert report["successful_predictions"] == 0
    assert "test-1" not in saved
    assert "private held-out" not in saved
