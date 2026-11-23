"""Inference wrapper for Ripple's Adaption-trained Gemma 3 4B LoRA adapter.

Model dependencies are imported only when loading weights so prompt and output
validation can be tested in the lightweight project environment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from data.adaption_trial.prepare_trial import COMPLETION_KEYS, INSTRUCTION, make_prompt
from data.evaluation import parse_prediction
from engine.models import SupplyNetwork

MODEL_LABEL = "Adaption-trained Gemma 3 4B LoRA"
DEFAULT_MAX_NEW_TOKENS = 512


@dataclass
class InferenceResult:
    scenario_id: str
    raw_model_output: str | None
    parsed_prediction: dict[str, Any] | None
    json_valid: bool
    field_completeness: bool
    node_references_valid: bool
    inference_duration_seconds: float
    model_identity: str
    checkpoint_identity: str
    base_model_id: str | None
    errors: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return (self.raw_model_output is not None and self.json_valid and self.field_completeness
                and self.node_references_valid and not self.errors)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["usable"] = self.usable
        return result


def _network_dict(network: SupplyNetwork | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(network, SupplyNetwork):
        raw = network.to_dict()
    elif isinstance(network, Mapping):
        raw = dict(network)
    else:
        raise TypeError("network must be a SupplyNetwork or network mapping")
    # Round-trip through the engine model for structural validation and a detached copy.
    return SupplyNetwork.from_dict(raw).to_dict()


def _failure_metadata(
    network: dict[str, Any], failed_nodes: Sequence[str],
    failure_type: str | None, failure_description: str | None,
) -> tuple[list[str], str, str]:
    if not isinstance(failed_nodes, (list, tuple)) or not failed_nodes:
        raise ValueError("failed_nodes must contain at least one facility ID")
    if any(not isinstance(node_id, str) or not node_id.strip() for node_id in failed_nodes):
        raise ValueError("failed_nodes must contain non-empty string IDs")
    failed = list(failed_nodes)
    if len(failed) != len(set(failed)):
        raise ValueError("failed_nodes must not contain duplicates")
    nodes = {node["id"]: node for node in network["nodes"]}
    unknown = sorted(set(failed) - set(nodes))
    if unknown:
        raise ValueError(f"failed_nodes contains unknown network IDs: {', '.join(unknown)}")
    inferred_type = "multiple" if len(failed) > 1 else nodes[failed[0]]["type"]
    actual_type = failure_type or inferred_type
    if not isinstance(actual_type, str) or actual_type not in {"supplier", "warehouse", "store", "multiple"}:
        raise ValueError("failure_type must be supplier, warehouse, store, or multiple")
    if actual_type != inferred_type:
        raise ValueError(f"failure_type {actual_type!r} does not match the failed facility IDs ({inferred_type!r})")
    if not isinstance(failure_description, (str, type(None))):
        raise ValueError("failure_description must be a string when provided")
    description = failure_description or (
        f"Failure of {', '.join(failed)} ({actual_type}) in a supplied {len(nodes)}-node network."
    )
    return failed, actual_type, description


def build_inference_prompt(
    network: SupplyNetwork | Mapping[str, Any],
    failed_nodes: Sequence[str],
    *,
    failure_type: str | None = None,
    failure_description: str | None = None,
) -> str:
    """Build the training prompt format using input fields only.

    When the training metadata is available, pass its failure type and description
    for the byte-compatible scenario wording. Otherwise those two fields are
    derived from the network and failed IDs; no engine outcomes are consulted.
    """
    network_data = _network_dict(network)
    failed, actual_type, description = _failure_metadata(
        network_data, failed_nodes, failure_type, failure_description,
    )
    return make_prompt({
        "network": network_data,
        "failed_nodes": failed,
        "failure_type": actual_type,
        "failure_description": description,
    })


def parse_model_output(raw_output: str, node_ids: set[str]) -> tuple[dict[str, Any] | None, bool, bool, bool, list[str]]:
    """Parse a response and validate its contract and all returned facility IDs."""
    try:
        decoded = json.loads(
            raw_output,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {token}")),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, False, False, False, ["Model response is not strict JSON."]
    if not isinstance(decoded, dict):
        return None, False, False, False, ["Model response JSON must be an object."]

    parsed = parse_prediction(raw_output)
    errors: list[str] = []
    if parsed.error == "prediction is missing required fields":
        missing = sorted(set(COMPLETION_KEYS) - set(decoded))
        errors.append("Model response is missing required fields: " + ", ".join(missing) + ".")
    elif parsed.error:
        errors.append(parsed.error)
    field_complete = parsed.value is not None
    references: set[str] = set()
    for key in ("direct_impacts", "second_order_impacts", "third_order_impacts",
                "further_impacts", "impacted_nodes"):
        values = decoded.get(key)
        if isinstance(values, list):
            references.update(value for value in values if isinstance(value, str))
    bottleneck = decoded.get("predicted_bottleneck")
    if isinstance(bottleneck, str):
        references.add(bottleneck)
    unexpected = sorted(references - node_ids)
    node_references_valid = not unexpected
    if unexpected:
        errors.append(f"Prediction references unknown network node IDs: {', '.join(unexpected)}")
    return decoded, True, field_complete, node_references_valid, errors


def _scenario_id(network: dict[str, Any], failed_nodes: Sequence[str]) -> str:
    payload = json.dumps({"network": network, "failed_nodes": list(failed_nodes)},
                         sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "scenario-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class AdaptionGemmaPredictor:
    """Load a local PEFT LoRA adapter over its configured Gemma base model."""

    def __init__(self, model: Any, tokenizer: Any, *, checkpoint_path: Path,
                 base_model_id: str, max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS) -> None:
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")
        self.model = model
        self.tokenizer = tokenizer
        self.checkpoint_path = checkpoint_path
        self.base_model_id = base_model_id
        self.max_new_tokens = max_new_tokens
        self.model_identity = MODEL_LABEL
        self.checkpoint_identity = str(checkpoint_path)
        self.adapter_applied = True

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        *,
        base_model_id: str | None = None,
        hf_token: str | None = None,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    ) -> "AdaptionGemmaPredictor":
        """Load checkpoint and configured Gemma base; requires a CUDA GPU."""
        path = Path(checkpoint_path).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"LoRA checkpoint directory does not exist: {path}")
        adapter_weights = path / "adapter_model.safetensors"
        adapter_config_path = path / "adapter_config.json"
        if not adapter_weights.is_file() or not adapter_config_path.is_file():
            raise FileNotFoundError("Checkpoint must contain adapter_model.safetensors and adapter_config.json")
        try:
            adapter_config = json.loads(adapter_config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Could not read a valid adapter_config.json") from exc
        configured_base = adapter_config.get("base_model_name_or_path")
        resolved_base = base_model_id or configured_base
        if not isinstance(resolved_base, str) or not resolved_base.strip():
            raise ValueError("Set base_model_id or provide base_model_name_or_path in adapter_config.json")

        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Inference dependencies are missing. Install model/requirements.txt in the Colab GPU runtime."
            ) from exc
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU is required; model loading was not attempted.")

        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        token = hf_token or os.environ.get("HF_TOKEN")
        base_model = AutoModelForCausalLM.from_pretrained(
            resolved_base,
            torch_dtype=dtype,
            device_map="auto",
            token=token,
        )
        model = PeftModel.from_pretrained(base_model, str(path), is_trainable=False)
        if not getattr(model, "peft_config", None):
            raise RuntimeError("PEFT did not report a loaded adapter; refusing to run inference.")
        model.eval()

        has_tokenizer_files = any((path / filename).is_file() for filename in (
            "tokenizer.json", "tokenizer.model", "spiece.model", "vocab.json",
        ))
        tokenizer_source = str(path) if has_tokenizer_files else resolved_base
        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_source,
            token=token,
            local_files_only=has_tokenizer_files,
        )
        return cls(model, tokenizer, checkpoint_path=path, base_model_id=resolved_base,
                   max_new_tokens=max_new_tokens)

    def predict_scenario(
        self,
        network: SupplyNetwork | Mapping[str, Any],
        failed_nodes: Sequence[str],
        *,
        scenario_id: str | None = None,
        failure_type: str | None = None,
        failure_description: str | None = None,
    ) -> InferenceResult:
        network_data = _network_dict(network)
        failed, actual_type, description = _failure_metadata(
            network_data, failed_nodes, failure_type, failure_description,
        )
        prompt = make_prompt({"network": network_data, "failed_nodes": failed,
                              "failure_type": actual_type, "failure_description": description})
        result_id = scenario_id or _scenario_id(network_data, failed)
        node_ids = {node["id"] for node in network_data["nodes"]}
        started = time.perf_counter()
        try:
            import torch

            encoded = self.tokenizer(prompt, return_tensors="pt")
            model_device = next(self.model.parameters()).device
            encoded = {key: value.to(model_device) for key, value in encoded.items()}
            with torch.inference_mode():
                generated = self.model.generate(
                    **encoded,
                    do_sample=False,
                    max_new_tokens=self.max_new_tokens,
                    pad_token_id=(self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None
                                  else self.tokenizer.eos_token_id),
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            input_length = encoded["input_ids"].shape[1]
            raw_output = self.tokenizer.decode(generated[0][input_length:], skip_special_tokens=True).strip()
            duration = time.perf_counter() - started
            parsed, json_valid, complete, refs_valid, errors = parse_model_output(raw_output, node_ids)
            return InferenceResult(result_id, raw_output, parsed, json_valid, complete, refs_valid,
                                   duration, self.model_identity, self.checkpoint_identity,
                                   self.base_model_id, errors)
        except Exception as exc:
            duration = time.perf_counter() - started
            return InferenceResult(result_id, None, None, False, False, False, duration,
                                   self.model_identity, self.checkpoint_identity,
                                   self.base_model_id, [f"Inference failed: {type(exc).__name__}: {exc}"])


def predict_scenario(
    predictor: AdaptionGemmaPredictor,
    network: SupplyNetwork | Mapping[str, Any],
    failed_nodes: Sequence[str],
    **metadata: Any,
) -> InferenceResult:
    """Functional convenience API over a previously loaded real predictor."""
    return predictor.predict_scenario(network, failed_nodes, **metadata)


__all__ = [
    "MODEL_LABEL", "COMPLETION_KEYS", "INSTRUCTION", "InferenceResult",
    "AdaptionGemmaPredictor", "build_inference_prompt", "parse_model_output",
    "predict_scenario",
]
