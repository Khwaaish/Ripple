import type { FacilityType, NetworkEdge, NetworkNode, SupplyNetwork } from './types'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isNetworkNode(value: unknown): value is NetworkNode {
  if (!isRecord(value)) return false
  const types: FacilityType[] = ['supplier', 'warehouse', 'store']
  return typeof value.id === 'string' && types.includes(value.type as FacilityType)
    && finite(value.capacity) && finite(value.load) && finite(value.buffer_hours)
    && typeof value.critical === 'boolean'
    && (value.criticality_weight === null || finite(value.criticality_weight))
    && finite(value.recovery_hours)
    && (value.unit_cost === null || finite(value.unit_cost))
}

function isNetworkEdge(value: unknown): value is NetworkEdge {
  return isRecord(value) && typeof value.src === 'string' && typeof value.dst === 'string'
    && finite(value.share) && finite(value.delay_h) && finite(value.capacity)
    && finite(value.reliability) && typeof value.is_alt === 'boolean'
}

/** Validate the real demo payload before giving it to the graph renderer. */
export function parseDemoNetwork(value: unknown): SupplyNetwork {
  if (!isRecord(value) || !Array.isArray(value.nodes) || !Array.isArray(value.edges)) {
    throw new ApiError('The demo network response must contain nodes and edges arrays.')
  }
  if (!value.nodes.every(isNetworkNode) || !value.edges.every(isNetworkEdge)) {
    throw new ApiError('The demo network response contains fields the map cannot render.')
  }
  const network: SupplyNetwork = { nodes: value.nodes, edges: value.edges }
  const nodeIds = new Set(network.nodes.map((node) => node.id))
  if (network.nodes.length !== 12 || network.edges.length !== 16) {
    throw new ApiError(`Expected the 12-node, 16-edge demo network; received ${network.nodes.length} nodes and ${network.edges.length} edges.`)
  }
  if (nodeIds.size !== network.nodes.length || network.edges.some((edge) => !nodeIds.has(edge.src) || !nodeIds.has(edge.dst))) {
    throw new ApiError('The demo network contains duplicate node IDs or edges with missing endpoints.')
  }
  return network
}

export async function fetchDemoNetwork(signal?: AbortSignal): Promise<SupplyNetwork> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/network/demo`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(`Could not reach the Ripple API at ${API_BASE_URL}. Check that the backend is running and retry.`)
  }
  if (!response.ok) {
    throw new ApiError(`Ripple API returned HTTP ${response.status} while loading the demo network.`, response.status)
  }
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiError('Ripple API returned a response that was not valid JSON.')
  }
  return parseDemoNetwork(payload)
}
