"""Pydantic request models for the Ripple HTTP API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class NodeInput(ApiModel):
    id: str = Field(min_length=1)
    type: Literal["supplier", "warehouse", "store"]
    capacity: float = Field(gt=0)
    load: float = Field(ge=0)
    buffer_hours: float = Field(default=0, ge=0)
    critical: bool = False
    criticality_weight: float | None = Field(default=None, gt=0)
    recovery_hours: float = Field(default=0, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)


class EdgeInput(ApiModel):
    src: str = Field(min_length=1)
    dst: str = Field(min_length=1)
    share: float = Field(ge=0, le=1)
    delay_h: float = Field(ge=0)
    capacity: float = Field(ge=0)
    reliability: float = Field(default=1, ge=0, le=1)
    is_alt: bool = False


class NetworkInput(ApiModel):
    nodes: list[NodeInput] = Field(min_length=1)
    edges: list[EdgeInput]


class SimulationRequest(ApiModel):
    network: NetworkInput
    failed_nodes: list[str] = Field(min_length=1)


class ComparisonRequest(ApiModel):
    network: NetworkInput
    failed_nodes: list[str] = Field(min_length=1)
