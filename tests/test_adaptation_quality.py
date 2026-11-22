import json

from data.adaption_trial.adaptation_quality import (
    compare_adapted_rows, original_quality_report, write_examples,
)
from data.adaption_trial.prepare_trial import COMPLETION_KEYS


def _target():
    return {
        "cascade_summary": "A fails.", "direct_impacts": ["A"],
        "second_order_impacts": [], "third_order_impacts": [], "further_impacts": [],
        "impacted_nodes": ["A"], "predicted_bottleneck": "A", "severity": "high",
        "ranked_mitigation_interventions": ["reroute"],
        "recommended_intervention": "reroute", "explanation": "Modeled result.",
    }


def _row():
    prompt = ('You are Ripple.\\nScenario input (JSON):\\n'
              '{"nodes":[{"id":"A"}],"failed_nodes":["A"]}'
              '\\n\\nOutput JSON schema: {}')
    return {"prompt": prompt, "completion": json.dumps(_target())}


def test_identical_target_matches_exact_prompt_and_preserves_labels():
    original = _row()
    report = compare_adapted_rows([original], [dict(original)], ["s1"])
    assert report["quality_checks"]["factual_target_preservation_rate"] == 1.0
    assert report["quality_checks"]["matched_records"][0]["method"] == "exact_prompt"
    assert report["quality_checks"]["changed_target_row_count"] == 0
    assert set(json.loads(original["completion"])) == set(COMPLETION_KEYS)


def test_changed_target_and_unknown_node_are_reported():
    original = _row()
    target = _target()
    target["severity"] = "critical"
    target["impacted_nodes"] = ["not-in-network"]
    adapted = {"original_prompt": original["prompt"], "enhanced_completion": json.dumps(target)}
    report = compare_adapted_rows([original], [adapted], ["s1"])
    assert report["quality_checks"]["changed_target_row_count"] == 1
    assert report["changed_targets"][0]["changed_fields"]["severity"] == {
        "original": "high", "adapted": "critical"}
    assert report["quality_checks"]["unsupported_claims"]


def test_malformed_unmatched_duplicate_and_missing_are_explicit():
    original = [_row(), _row()]
    adapted = [
        {"prompt": "rewritten with no original field", "completion": "not json"},
        dict(original[0]),
        dict(original[0]),
    ]
    report = compare_adapted_rows(original, adapted)
    stats = report["dataset_statistics"]
    assert stats["adapted_rows"] == 3
    assert stats["missing_records"] == 2
    assert stats["ambiguous_adapted_row_indices"] == [1, 2]
    assert stats["extra_or_unmatched_records"] == 3
    assert report["quality_checks"]["malformed_outputs"]
    assert report["dataset_statistics"]["adapted_duplicate_prompt_completion_rows"] == 1


def test_not_run_report_and_examples_do_not_invent_adapted_output():
    from pathlib import Path
    import tempfile

    rows = [_row()]
    report = original_quality_report(rows)
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        example_path = Path(temp) / "examples.md"
        write_examples(example_path, rows, None, None)
        assert report["status"] == "adaptation_not_run"
        assert report["dataset_statistics"]["adapted_rows"] is None
        assert "No adaptation has been run" in example_path.read_text(encoding="utf-8")
