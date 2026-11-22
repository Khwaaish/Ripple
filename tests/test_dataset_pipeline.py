import json
from pathlib import Path
import tempfile

from data.generate_dataset import build_record, generate_splits, write_jsonl
from data.validate_dataset import validate_dataset, validate_record
from engine.scenario_generator import generate_scenario


def topology_signature(seed):
    n = generate_scenario(seed).network
    return tuple((e.src, e.dst, round(e.share, 3), e.is_alt) for e in n.edges)

def test_scenario_same_seed_is_reproducible():
    a, b = generate_scenario(321), generate_scenario(321)
    assert a.to_metadata("train-321", "train") == b.to_metadata("train-321", "train")
    assert a.failed_nodes == b.failed_nodes

def test_scenario_variety_in_topology_and_node_sizes():
    generated = [generate_scenario(seed) for seed in range(100, 140)]
    assert len({topology_signature(seed) for seed in range(100, 140)}) >= 35
    assert {len(x.network.nodes) for x in generated} >= set(range(6, 13))
    assert all({x.type for x in s.network.nodes.values()} == {"supplier", "warehouse", "store"} for s in generated)

def test_failure_sets_exist_and_have_dependencies():
    for seed in range(100):
        scenario = generate_scenario(seed)
        assert scenario.failed_nodes
        assert set(scenario.failed_nodes) <= scenario.network.nodes.keys()
        assert scenario.failure_type in {"supplier", "warehouse", "store", "multiple"}
        if scenario.failure_type != "store":
            assert any(e.src in scenario.failed_nodes for e in scenario.network.edges)

def test_train_test_generation_is_seed_disjoint_and_stable():
    t1, e1 = generate_splits(3, 2, 100, 900)
    t2, e2 = generate_splits(3, 2, 100, 900)
    assert t1 == t2 and e1 == e2
    assert {x["scenario_id"] for x in t1}.isdisjoint(x["scenario_id"] for x in e1)
    assert {x["seed"] for x in t1}.isdisjoint(x["seed"] for x in e1)
    assert {x["split"] for x in t1} == {"train"}
    assert {x["split"] for x in e1} == {"test"}

def test_record_labels_are_engine_derived():
    record = build_record(1234, "train")
    errors = []
    validate_record(record, "train", errors)
    assert not errors
    record["ground_truth"]["baseline"]["impact_score"] = 0.999999
    errors = []
    validate_record(record, "train", errors)
    assert any("fresh engine simulation" in error for error in errors)

def test_dataset_duplicate_and_schema_validation():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        root = Path(temp)
        record = build_record(701, "train")
        duplicate = json.loads(json.dumps(record))
        duplicate["scenario_id"] = "train-copy"
        duplicate["seed"] = 702
        train_path, test_path = root / "train.jsonl", root / "test.jsonl"
        write_jsonl(train_path, [record, duplicate])
        write_jsonl(test_path, [])
        report = validate_dataset(train_path, test_path, expected_train=2, expected_test=0)
        assert report["duplicate_scenarios"] == 1
        assert report["duplicate_ids"] == 0
        assert report["schema_validation_failure_count"] > 0

def test_jsonl_malformed_row_is_reported():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        root = Path(temp)
        path = root / "broken.jsonl"
        path.write_text('{bad json}\n', encoding="utf-8")
        report = validate_dataset(path, root / "missing.jsonl", expected_train=0, expected_test=0)
        assert report["schema_validation_failure_count"] >= 2
