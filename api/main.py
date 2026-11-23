"""Ripple FastAPI application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ComparisonRequest, SimulationRequest
from .service import compare_payload, demo_network_payload, simulate_payload

app = FastAPI(
    title="Ripple API",
    description="HTTP API for Ripple's deterministic cascading-failure simulator.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    # Vite uses 5173 by default and moves to 5174 when that port is occupied.
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ripple-api"}


@app.get("/network/demo")
async def demo_network() -> dict:
    return demo_network_payload()


@app.post("/simulate")
async def simulate_endpoint(request: SimulationRequest) -> dict:
    try:
        return simulate_payload(request.network, request.failed_nodes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/compare")
async def compare_endpoint(request: ComparisonRequest) -> dict:
    try:
        return compare_payload(request.network, request.failed_nodes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
