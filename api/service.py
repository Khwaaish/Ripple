"""Translate HTTP payloads into engine inputs and serialize engine results."""
from __future__ import annotations

from typing import Any

from engine.interventions import compare_interventions
from engine.models import SupplyNetwork
from engine.network_gen import create_sample_network
from engine.simulate import simulate

from .schemas import NetworkInput


def network_from_payload(payload: NetworkInput | dict[str, Any]) -> SupplyNetwork:
    """Build and validate a fresh engine network from a JSON-compatible payload."""
    data = payload.model_dump() if isinstance(payload, NetworkInput) else payload
    # from_dict creates new Node/Edge instances; copy makes the no-mutation boundary
    # explicit if this service is also called directly with an engine object later.
    return SupplyNetwork.from_dict(data).copy()


def simulate_payload(payload: NetworkInput, failed_nodes: list[str]) -> dict[str, Any]:
    network = network_from_payload(payload)
    return simulate(network, list(failed_nodes)).to_dict()


def compare_payload(payload: NetworkInput, failed_nodes: list[str]) -> dict[str, Any]:
    network = network_from_payload(payload)
    return compare_interventions(network, list(failed_nodes)).to_dict()


def demo_network_payload() -> dict[str, Any]:
    """Return a fresh JSON-compatible copy of the canonical 12-node network."""
    return create_sample_network().to_dict()
