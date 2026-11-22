import json
from pathlib import Path
import tempfile

import pytest

from data.adaption_trial import adaption_trial_client as client_util
from data.adaption_trial.prepare_trial import (
    COMPLETION_KEYS, INSTRUCTION, TRAIN_PATH, _main, convert_record, load_jsonl,
    make_completion, make_prompt, select_trial_records, validate_trial,
)


def train_rows():
    return load_jsonl(TRAIN_PATH)

def test_converter_schema_and_json_completion():
    record = train_rows()[0]
    converted = convert_record(record)
    assert set(converted) == {"prompt", "completion"}
    assert converted["prompt"].startswith(INSTRUCTION)
    completion = json.loads(converted["completion"])
    assert tuple(completion) == tuple(sorted(COMPLETION_KEYS))
    assert set(completion) == set(COMPLETION_KEYS)

def test_completion_preserves_engine_target_values():
    record = train_rows()[4]
    completion = json.loads(make_completion(record))
    target = record["ai_target"]
    assert completion["cascade_summary"] == target["cascade_summary"]
    assert completion["direct_impacts"] == target["direct_impacts"]
    assert completion["second_order_impacts"] == target["second_order_impacts"]
    assert completion["third_order_impacts"] == target["third_order_impacts"]
    assert completion["further_impacts"] == target["further_impacts"]
    assert completion["impacted_nodes"] == target["structured_response"]["impacted_nodes"]
    assert completion["predicted_bottleneck"] == target["predicted_bottleneck"]
    assert completion["severity"] == target["severity"]
    assert completion["ranked_mitigation_interventions"] == target["ranked_mitigation_interventions"]
    assert completion["recommended_intervention"] == target["structured_response"]["recommended_intervention"]

def test_selection_is_exactly_50_and_reproducible():
    rows = train_rows()
    first = select_trial_records(rows, count=50, seed=9876)
    second = select_trial_records(rows, count=50, seed=9876)
    assert len(first) == 50
    assert [r["scenario_id"] for r in first] == [r["scenario_id"] for r in second]
    assert all(r["split"] == "train" for r in first)

def test_nontraining_source_is_rejected():
    rows = train_rows()[:50]
    rows.append({**rows[0], "scenario_id": "test-not-allowed", "split": "test"})
    with pytest.raises(ValueError, match="non-training"):
        select_trial_records(rows, count=50, seed=1)

def test_prompt_is_consistent_and_excludes_ground_truth():
    rows = train_rows()[:8]
    prompts = [make_prompt(r) for r in rows]
    assert all(p.startswith(INSTRUCTION) for p in prompts)
    assert all("Scenario input (JSON):" in p and "Output JSON schema:" in p for p in prompts)
    assert all('"ground_truth"' not in p and '"impact_score"' not in p for p in prompts)

def test_trial_validation_checks_pair_to_source_mapping():
    source = train_rows()[:50]
    ids = [r["scenario_id"] for r in source]
    converted = [convert_record(r) for r in source]
    validate_trial(converted, source, ids)
    broken = list(converted)
    changed = json.loads(broken[0]["completion"])
    changed["severity"] = "low" if changed["severity"] != "low" else "high"
    broken[0] = {**broken[0], "completion": json.dumps(changed, sort_keys=True)}
    with pytest.raises(ValueError, match="does not match source target"):
        validate_trial(broken, source, ids)

def test_default_cli_is_local_only(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prepare_trial"])
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        monkeypatch.setattr(client_util, "REPORT_PATH", Path(temp) / "local_only_report.json")
        monkeypatch.setattr(client_util, "load_api_key_environment", lambda: False)
        monkeypatch.setattr(client_util, "run_api_actions", lambda **_: (_ for _ in ()).throw(AssertionError("API called")))
        _main()
        output = json.loads(capsys.readouterr().out)
        assert output["mode"] == "local_only"
        assert output["rows"] == 50
        assert output["upload_status"] == "not_attempted"

def test_api_client_requires_explicit_upload_and_fixed_trial_path():
    with pytest.raises(ValueError, match="requires the saved trial"):
        client_util.run_api_actions(upload=False, estimate=True)
    with pytest.raises(ValueError, match="Only data/adaption_trial"):
        client_util._validate_only_trial_file(TRAIN_PATH)

def test_secret_is_never_printed_or_saved(monkeypatch, capsys):
    secret = "DUMMY_NEVER_PRINT_THIS_12345"
    monkeypatch.setenv("ADAPTION_API_KEY", secret)
    monkeypatch.setattr(client_util, "load_api_key_environment", lambda: True)
    report = client_util.local_report({"conversion_version": "1.0", "record_count": 50,
                                       "selected_scenario_ids": ["train-id"], "source_split": "train",
                                       "trial_sha256": "hash"})
    assert secret not in json.dumps(report)
    assert secret not in capsys.readouterr().out
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        report_path = Path(temp) / "safe_report.json"
        monkeypatch.setattr(client_util, "REPORT_PATH", report_path)
        client_util.save_safe_report(report)
        saved = report_path.read_text(encoding="utf-8")
        assert secret not in saved
        assert json.loads(saved)["api_key_configured"] is True


def test_trial_file_has_50_rows_and_no_test_ids():
    from data.adaption_trial.prepare_trial import METADATA_PATH, TRIAL_PATH
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    trial_rows = load_jsonl(TRIAL_PATH)
    test_ids = {row["scenario_id"] for row in load_jsonl(TRAIN_PATH.parent / "test.jsonl")}
    assert len(trial_rows) == 50
    assert all(set(row) == {"prompt", "completion"} for row in trial_rows)
    assert not set(metadata["selected_scenario_ids"]) & test_ids
    assert all(isinstance(json.loads(row["completion"]), dict) for row in trial_rows)


def test_estimate_helper_uses_estimate_true_only():
    from types import SimpleNamespace
    calls = {}
    class Datasets:
        def adapt(self, dataset_id, **kwargs):
            calls["dataset_id"] = dataset_id
            calls.update(kwargs)
            return SimpleNamespace(estimate=True, estimated_credits_consumed=1, estimated_minutes=11)
    result = client_util._request_estimate(SimpleNamespace(datasets=Datasets()), "dataset-1",
        {"ingested_row_count": 50, "column_mapping_verified": False})
    assert calls["estimate"] is True
    assert calls["column_mapping"] == {"prompt": "prompt", "completion": "completion"}
    assert result["estimated_credits"] == 1
    assert result["adaptation_started"] is False
