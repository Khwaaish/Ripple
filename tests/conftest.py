"""Prepare small deterministic JSONL datasets locally for tests when absent."""
from pathlib import Path

import pytest

from data.generate_dataset import generate_splits, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "train.jsonl"
TEST_PATH = ROOT / "data" / "test.jsonl"


@pytest.fixture(scope="session", autouse=True)
def ensure_local_generated_datasets() -> None:
    """Keep generated train/test data reproducible but out of the public source tree."""
    if TRAIN_PATH.exists() and TEST_PATH.exists():
        return

    train_rows, test_rows = generate_splits(
        train_count=60,
        test_count=30,
        train_seed_start=100_000,
        test_seed_start=900_000,
    )
    if not TRAIN_PATH.exists():
        write_jsonl(TRAIN_PATH, train_rows)
    if not TEST_PATH.exists():
        write_jsonl(TEST_PATH, test_rows)
