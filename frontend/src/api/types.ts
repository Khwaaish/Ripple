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
