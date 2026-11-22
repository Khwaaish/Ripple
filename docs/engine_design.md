# Engine design

## Network model

`Node` records an identifier, facility type, capacity, normal load, buffer, criticality, recovery time, and optional unit cost. `Edge` records the directed share, maximum link flow, delay, reliability, and alternate status. `SupplyNetwork` stores these records and a NetworkX `DiGraph`; duplicate references and directed cycles are rejected. Serialization uses plain dictionaries and lists.

## Propagation and cascade rounds

For an edge `u -> v`, its nominal flow is `min(v.load * edge.share, edge.capacity) * edge.reliability`. A failed source removes that flow. A source's lost fraction is applied to its outgoing edge flows; destination shortage is capped at its load. Only nodes with a positive calculated loss propagate that loss in the next round. Rounds are deterministic, sorted by node/edge ID, stop when there is no change, and default to a maximum of five. The first arrival time follows the shortest encountered loss path by accumulated edge delay. A shortage appears when it arrives; predicted stockout time adds the destination buffer to that arrival.

`round_snapshots` records newly affected nodes and cumulative shortages. Impact layers are assigned by the first propagation round in which each node receives a shortage.

## Interventions

- `none` keeps the failed supply unavailable.
- `reroute` covers shortage through inbound edges marked `is_alt`, bounded by alternate source spare capacity, link capacity, destination share, and reliability.
- `backup_supplier` applies one finite pool (default 60% of the first failed node's capacity) after the configured activation delay; its optional operational cost is reported.
- `prioritize` uses the same bounded alternate allocation as reroute and annotates the critical-node policy in reasoning. As a compact prototype, prioritization currently gives critical destinations an explicit priority classification but does not reallocate a shared global pool across competing destinations.

Each scenario is run through `simulate`; comparisons use the identical result schema and rank by weighted impact, recovery time, then cost.

## Impact and severity

Let `L_i` be unmet demand at non-failed node `i`, `w_i` its criticality weight, and `D` total network load. The normalized score is:

`min(1, sum_i(L_i * w_i) / D)`

Failed nodes are excluded from the numerator because the metric scores downstream unmet demand. They remain in the failed-node list and recovery estimate. Severity thresholds are low at 0, medium above 0 through 0.25, high from 0.25 through below 0.5, and critical at 0.5 or above.

Recovery estimate is the maximum of affected-node recovery hours plus calculated shortage (in model time units); it is a transparent heuristic, not a logistics forecast. Bottleneck is the impacted node with the largest weighted unmet demand.

## Assumptions and limitations

This is a hackathon simulation, not real-world logistics forecasting. Loads and capacities use consistent but otherwise unspecified units. The model treats edge shares as nominal destination-demand fractions; overload pressure on a reroute is applied as downstream shortage, but the engine does not optimize a full multi-commodity flow, infer hidden supplier relationships, model stochastic failures, or model time-varying demand. Reliability scales expected flow deterministically rather than sampling failures. Stockout handling is simplified, and intervention competition across multiple destinations is limited. Validate the model against operational data before using it for real decisions.
