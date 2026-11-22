import type { Edge, Node } from '@xyflow/react'
import type { NetworkEdge, NetworkNode } from '../../api/types'

export type FacilityNodeData = { facility: NetworkNode; selected: boolean }
export type FacilityFlowNode = Node<FacilityNodeData, 'facility'>
export type SupplyEdgeData = { supply: NetworkEdge; labelOffsetY: number }
export type SupplyFlowEdge = Edge<SupplyEdgeData, 'supply'>
