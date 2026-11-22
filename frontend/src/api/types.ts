export type FacilityType = 'supplier' | 'warehouse' | 'store'

/** Matches engine.models.Node as returned by GET /network/demo. */
export type NetworkNode = {
  id: string
  type: FacilityType
  capacity: number
  load: number
  buffer_hours: number
  critical: boolean
  criticality_weight: number | null
  recovery_hours: number
  unit_cost: number | null
}

/** Matches engine.models.Edge as returned by GET /network/demo. */
export type NetworkEdge = {
  src: string
  dst: string
  share: number
  delay_h: number
  capacity: number
  reliability: number
  is_alt: boolean
}

export type SupplyNetwork = {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

/** Matches engine.simulate.SimulationResult as returned by POST /simulate. */
export type SimulationResult = {
  failed_nodes: string[]
  directly_impacted_nodes: string[]
  second_order_impacted_nodes: string[]
  third_order_impacted_nodes: string[]
  further_impacted_nodes: string[]
  all_impacted_nodes: string[]
  overloaded_nodes: string[]
  critical_shortage_nodes: string[]
  bottleneck_node: string | null
  first_predicted_stockout_time_h: number | null
  propagation_rounds: number
  impact_score: number
  severity: string
  round_snapshots: Array<{
    round: number
    newly_impacted: string[]
    losses: Record<string, number>
    overloaded_nodes: string[]
  }>
  node_impacts: Record<string, {
    lost_supply: number
    shortage: number
    shortage_fraction: number
    stockout_time_h: number | null
    critical: boolean
  }>
  recovery_estimate_h: number
  intervention: string
  intervention_cost: number
  reasoning: string[]
}

export type ScenarioRun = {
  network: SupplyNetwork
  result: SimulationResult
}
