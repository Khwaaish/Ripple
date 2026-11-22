# Ripple: Cascading Failure Intelligence

Ripple is a deterministic, rule-based prototype for exploring how supply interruptions can cascade across suppliers, warehouses, and stores. Its simulation engine is the numeric source of truth; downstream AI features should explain calculated results rather than invent them.

## Setup

Python 3.11+ is recommended. Install the small dependency set and run tests:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

## Run a simulation

```python
from engine.network_gen import create_sample_network
from engine.simulate import simulate
from engine.interventions import compare_interventions

network = create_sample_network()
result = simulate(network, failed_nodes=["WH1"], intervention="none")
print(result.to_dict())
print(compare_interventions(network, ["WH1"]).to_dict())
```

## Run the local API

Install the dependencies, then start the FastAPI development server from the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive docs are at `/docs`. The local Vite origins `http://localhost:5173` and `http://127.0.0.1:5173` are enabled for CORS.

Example requests:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/network/demo
curl -X POST http://127.0.0.1:8000/simulate -H "Content-Type: application/json" -d '{"network":{"nodes":[{"id":"W","type":"warehouse","capacity":30,"load":20},{"id":"A","type":"store","capacity":10,"load":8}],"edges":[{"src":"W","dst":"A","share":1,"delay_h":2,"capacity":8}]},"failed_nodes":["W"]}'
curl -X POST http://127.0.0.1:8000/compare -H "Content-Type: application/json" -d '{"network":{"nodes":[{"id":"W","type":"warehouse","capacity":30,"load":20},{"id":"A","type":"store","capacity":10,"load":8}],"edges":[{"src":"W","dst":"A","share":1,"delay_h":2,"capacity":8}]},"failed_nodes":["W"]}'
```

## Generate and validate scenarios

Batch 2 adds reproducible scenario generation and a 2,300-record dataset pipeline:

```bash
python -m data.generate_dataset
python -m data.validate_dataset
```

Training data and held-out evaluation data are written separately. See [data/README.md](data/README.md) for schema, seed ranges, validation rules, and quality report details. See [docs/engine_design.md](docs/engine_design.md) for simulation formulas, assumptions, and limitations.
