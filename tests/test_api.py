from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine.network_gen import create_sample_network

client = TestClient(app)


def payload():
    return {
        "network": {
            "nodes": [
                {"id": "W", "type": "warehouse", "capacity": 30, "load": 20},
                {"id": "A", "type": "store", "capacity": 10, "load": 8, "buffer_hours": 4},
            ],
            "edges": [{"src": "W", "dst": "A", "share": 1, "delay_h": 2, "capacity": 8}],
        },
        "failed_nodes": ["W"],
    }


def test_health_endpoint_reports_ready_service():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ripple-api"}


def test_demo_endpoint_returns_deterministic_12_node_network():
    first = client.get("/network/demo")
    second = client.get("/network/demo")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["nodes"]) == 12
    assert len(first.json()["edges"]) == 16


def test_simulate_endpoint_returns_engine_metrics_and_is_deterministic():
    request = payload()
    before = deepcopy(request)
    first = client.post("/simulate", json=request)
    second = client.post("/simulate", json=request)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert request == before
    result = first.json()
    assert result["failed_nodes"] == ["W"]
    assert result["directly_impacted_nodes"] == ["A"]
    assert result["severity"] == "high"
    assert result["bottleneck_node"] == "A"
    assert result["first_predicted_stockout_time_h"] == 6
    assert result["round_snapshots"]
    assert result["node_impacts"]["A"]["stockout_time_h"] == 6


def test_compare_endpoint_returns_all_strategies_and_recommendation():
    response = client.post("/compare", json=payload())
    assert response.status_code == 200
    result = response.json()
    assert set(result["scenarios"]) == {"none", "reroute", "backup_supplier", "prioritize"}
    assert result["recommended_strategy"] in result["scenarios"]
    assert result["ranking"][0] == result["recommended_strategy"]
    assert "Selected" in result["recommendation_reason"]


def test_invalid_network_and_unknown_failed_node_return_helpful_422():
    invalid_graph = payload()
    invalid_graph["network"]["edges"].append(
        {"src": "A", "dst": "W", "share": 1, "delay_h": 0, "capacity": 2}
    )
    response = client.post("/simulate", json=invalid_graph)
    assert response.status_code == 422
    assert "acyclic" in response.json()["detail"]

    unknown = payload()
    unknown["failed_nodes"] = ["missing"]
    response = client.post("/compare", json=unknown)
    assert response.status_code == 422
    assert "Unknown failed node" in response.json()["detail"]


def test_request_schema_rejects_invalid_node_fields():
    request = payload()
    request["network"]["nodes"][0]["type"] = "factory"
    response = client.post("/simulate", json=request)
    assert response.status_code == 422


def test_demo_result_does_not_mutate_shared_network_factory_output():
    before = create_sample_network().to_dict()
    response = client.get("/network/demo")
    response.json()["nodes"].clear()
    assert create_sample_network().to_dict() == before


@pytest.mark.parametrize("origin", [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
])
@pytest.mark.parametrize("path", ["/simulate", "/compare"])
def test_vite_cors_preflight_allows_local_frontend_origin(origin, path):
    response = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "accept,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_demo_network_get_allows_current_vite_fallback_origin():
    origin = "http://127.0.0.1:5174"
    response = client.get("/network/demo", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert len(response.json()["nodes"]) == 12
    assert len(response.json()["edges"]) == 16
