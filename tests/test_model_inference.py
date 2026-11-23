from __future__ import annotations

from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data.adaption_trial.prepare_trial import INSTRUCTION, make_prompt
from engine.scenario_generator import generate_scenario
from model.colab_smoke_test import run_smoke_test, select_smoke_scenarios
from model.inference import (
    AdaptionGemmaPredictor,
    MODEL_LABEL,
    build_inference_prompt,
    parse_model_output,
)


def _scenario():
    scenario = generate_scenario(100_123, "train")
    metadata = scenario.to_metadata("train-00100123", "train")
    return scenario, metadata


def _valid_prediction() -> dict:
    return {
        "cascade_summary": "No downstream shortages are modeled.",
        "direct_impacts": [],
        "second_order_impacts": [],
        "third_order_impacts": [],
        "further_impacts": [],
        "impacted_nodes": [],
        "predicted_bottleneck": None,
        "severity": "low",
        "ranked_mitigation_interventions": ["none", "reroute", "backup_supplier", "prioritize"],
        "recommended_intervention": "none",
        "explanation": "Test-only structured response.",
    }


def test_prompt_matches_existing_training_template_without_passing_labels() -> None:
    scenario, record = _scenario()
    prompt = build_inference_prompt(
        record["network"], record["failed_nodes"],
        failure_type=record["failure_type"],
        failure_description=record["failure_description"],
    )
    expected = make_prompt({key: record[key] for key in (
        "network", "failed_nodes", "failure_type", "failure_description",
    )})

    assert prompt == expected
    assert prompt.startswith(INSTRUCTION)
    assert "ground_truth" not in prompt
    assert "impact_score" not in prompt
    assert scenario.failed_nodes == record["failed_nodes"]


def test_prompt_rejects_unknown_or_mismatched_failed_facilities() -> None:
    scenario, record = _scenario()
    with pytest.raises(ValueError, match="unknown network IDs"):
        build_inference_prompt(record["network"], ["UNKNOWN"])
    with pytest.raises(ValueError, match="does not match"):
        build_inference_prompt(record["network"], record["failed_nodes"], failure_type="store")
    assert scenario.network.to_dict() == record["network"]


def test_valid_json_output_has_required_fields_and_known_node_references() -> None:
    _, record = _scenario()
    node_ids = {node["id"] for node in record["network"]["nodes"]}
    prediction = _valid_prediction()
    prediction["direct_impacts"] = [record["network"]["nodes"][-1]["id"]]

    parsed, json_valid, complete, references_valid, errors = parse_model_output(
        json.dumps(prediction), node_ids,
    )

    assert parsed == prediction
    assert json_valid and complete and references_valid
    assert errors == []


def test_malformed_json_is_reported_without_prediction() -> None:
    parsed, json_valid, complete, references_valid, errors = parse_model_output("{bad", {"A"})

    assert parsed is None
    assert not json_valid and not complete and not references_valid
    assert errors == ["Model response is not strict JSON."]


def test_missing_fields_preserve_parsed_json_but_mark_incomplete() -> None:
    parsed, json_valid, complete, references_valid, errors = parse_model_output(
        json.dumps({"severity": "low"}), {"A"},
    )

    assert parsed == {"severity": "low"}
    assert json_valid
    assert not complete and references_valid
    assert "missing required fields" in errors[0]


def test_unknown_predicted_node_is_rejected_as_unusable() -> None:
    prediction = _valid_prediction()
    prediction["direct_impacts"] = ["UNEXPECTED"]

    parsed, json_valid, complete, references_valid, errors = parse_model_output(
        json.dumps(prediction), {"S1", "WH1"},
    )

    assert parsed == prediction
    assert json_valid and complete
    assert not references_valid
    assert any("UNEXPECTED" in message for message in errors)


def test_smoke_scenario_selector_is_fixed_to_five_train_records() -> None:
    rows = [generate_scenario(seed, "train").to_metadata(f"train-{seed}", "train")
            for seed in range(100_100, 100_120)]

    selected = select_smoke_scenarios(rows)

    assert len(selected) == 5
    assert all(row["split"] == "train" for row in selected)
    assert [row["scenario_id"] for row in selected] == [row["scenario_id"] for row in select_smoke_scenarios(rows)]
    with pytest.raises(ValueError, match="training-split"):
        select_smoke_scenarios([*rows[:4], {**rows[4], "split": "test"}])
    with pytest.raises(ValueError, match="exactly five"):
        select_smoke_scenarios(rows, count=4)


def test_missing_checkpoint_stops_before_model_imports(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="checkpoint directory"):
        AdaptionGemmaPredictor.from_checkpoint(tmp_path / "absent")


def test_smoke_runner_rejects_heldout_path_before_reading_or_model_load(tmp_path: Path) -> None:
    heldout_path = tmp_path / "test.jsonl"
    heldout_path.write_text("not parsed", encoding="utf-8")

    with pytest.raises(ValueError, match="Held-out test"):
        run_smoke_test(tmp_path / "checkpoint", heldout_path)


def test_generation_errors_are_returned_explicitly(monkeypatch, tmp_path: Path) -> None:
    class Tensor:
        shape = (1, 2)
        device = "cuda:0"

        def to(self, _device):
            return self

    class Tokenizer:
        pad_token_id = 0
        eos_token_id = 2

        def __call__(self, *_args, **_kwargs):
            return {"input_ids": Tensor()}

    class FailingModel:
        def parameters(self):
            return iter([Tensor()])

        def generate(self, **_kwargs):
            raise RuntimeError("test generation failure")

    monkeypatch.setitem(__import__("sys").modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    predictor = AdaptionGemmaPredictor(
        FailingModel(), Tokenizer(), checkpoint_path=tmp_path,
        base_model_id="google/gemma-3-4b-pt",
    )
    scenario, record = _scenario()

    result = predictor.predict_scenario(record["network"], record["failed_nodes"], scenario_id=record["scenario_id"])

    assert result.model_identity == MODEL_LABEL
    assert result.raw_model_output is None
    assert not result.usable
    assert "test generation failure" in result.errors[0]
    assert scenario.network.to_dict() == record["network"]
