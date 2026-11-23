# Ripple Colab GPU inference smoke test

This package loads Ripple's actual Adaption-trained Gemma 3 4B PT LoRA adapter
with its configured base model. It runs exactly five infrastructure smoke
scenarios from the **training split**. It does not run the held-out test set,
perform model evaluation, call Adaption, or substitute engine outputs for model
responses.

The model is identified as **Adaption-trained Gemma 3 4B LoRA**. Results from
these five training examples are not an unbiased quality measure.

## 1. Prepare the Colab runtime

1. In Colab choose **Runtime → Change runtime type → GPU**. Select an available
   GPU runtime and run the GPU check below before loading weights. This wrapper
   loads in FP16/BF16 without quantization and requires at least 12 GiB of free
   GPU memory before loading (roughly 8 GiB for 4B base weights plus adapter,
   runtime, and generation-cache headroom).
2. Make the Ripple source available under `/content/Ripple` by cloning your
   repository's actual remote URL or uploading the source archive. No remote URL
   or local workstation path is assumed here.
3. Mount Google Drive (or upload the files through Colab) so the checkpoint and
   `data/train.jsonl` are accessible. The checkpoint directory must contain
   `adapter_model.safetensors` and `adapter_config.json`; it should also contain
   the tokenizer assets exported with the adapter. Keep the original checkpoint
   files unchanged.

Example Colab cells (replace the paths with the paths in your mounted Drive):

```python
from google.colab import drive
drive.mount('/content/drive')

%cd /content/Ripple
!python - <<'PY'
import torch
assert torch.cuda.is_available(), 'Select a Colab GPU runtime first'
print(torch.cuda.get_device_name(0))
print(f'Free GPU memory: {torch.cuda.mem_get_info(0)[0] / 1024**3:.1f} GiB')
PY
!python -m pip install -r model/requirements.txt
```

The requirements deliberately do not install PyTorch: Colab supplies a
CUDA-matched build. If PyTorch is absent, use the official PyTorch install
selector for the runtime's CUDA version rather than installing a CPU wheel.

## 2. Check model access

The script reads `base_model_name_or_path` from the adapter's
`adapter_config.json`, unless an explicit `--base-model-id` override is passed.
Review that value and confirm it names the trained Gemma 3 4B PT base model
before running. Do not substitute another Gemma variant.

Hugging Face's official `google/gemma-3-4b-pt` model page requires an account to
review and accept Google's Gemma usage terms before its files can be accessed.
If that is the configured base model, accept the terms while signed in to
Hugging Face. If Colab's access is not already authenticated, add an `HF_TOKEN`
as a Colab Secret and expose it to the runtime without printing it:

```python
from google.colab import userdata
import os
os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN')
```

Never paste a token into a notebook cell or command history. Authentication is
only needed to fetch the configured base model if access is gated; the local
adapter itself is read from the mounted checkpoint directory.

Official references: [Gemma 3 4B PT model card](https://huggingface.co/google/gemma-3-4b-pt),
[Transformers Gemma 3 documentation](https://huggingface.co/docs/transformers/model_doc/gemma3).
Gemma 3 support requires Transformers 4.50 or later; the requirements file
keeps the install within the Transformers 4.x series supported by this wrapper.

## 3. Run exactly five training-only smoke scenarios

```python
!python -m model.colab_smoke_test \
  --checkpoint "/content/drive/MyDrive/path/to/extracted-adaption-checkpoint" \
  --train-data "/content/drive/MyDrive/ripple-data/train.jsonl" \
  --output-dir "/content/drive/MyDrive/ripple-inference-smoke"
```

`--checkpoint` and `--train-data` are configurable paths. The train file must
contain JSONL scenario records marked `"split":"train"`; any non-training row
causes the script to stop before loading the model. The selector chooses five
varied records using only split metadata, failure type, difficulty, network
size, and failure count. Ground-truth labels are never passed into generation.
The smoke test count is fixed at five and cannot be overridden.

The run writes:

- `raw_model_outputs.jsonl` — each raw response, timing, model/checkpoint
  identity, parse/completeness status, and validation errors.
- `parsed_predictions.jsonl` — parsed JSON when available plus validation
  status. Malformed output remains visible in the raw file and is not replaced.
- `smoke_test_report.json` — GPU details and aggregate infrastructure status;
  it explicitly marks this as a smoke test, not a performance evaluation.

No held-out examples or ground-truth completions are written to the outputs.
Store the output directory outside the repository or under the ignored
`data/evaluation/` folder.

## Implementation notes and boundaries

- `model/inference.py` reuses Ripple's training prompt builder and completion
  schema. It validates JSON types, required fields, strategies, and all
  predicted facility references against the input network.
- The wrapper loads the base identifier from the checkpoint config, loads
  tokenizer files from the checkpoint when present, applies the LoRA via PEFT,
  and reports load/generation errors explicitly.
- The runtime requires a CUDA GPU. It does not silently fall back to CPU, a
  different model, deterministic engine results, or synthetic predictions.
- No full evaluation on `data/test.jsonl` is part of this command.
