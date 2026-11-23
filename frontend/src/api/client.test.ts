import { describe, expect, it, vi } from 'vitest'
import { ApiError, compareNetworkStrategies, parseDemoNetwork, simulateNetwork } from './client'
import { demoNetworkFixture } from '../test/demoNetwork'
import { demoInterventionComparison } from '../test/interventionComparison'

describe('demo network API schema', () => {
  it('accepts the verified 12-node, 16-edge backend payload shape', () => {
    const network = parseDemoNetwork(demoNetworkFixture)
    expect(network.nodes).toHaveLength(12)
    expect(network.edges).toHaveLength(16)
    expect(network.nodes[0]).toMatchObject({ id: 'S1', type: 'supplier', capacity: 150, load: 115 })
    expect(network.edges[1]).toMatchObject({ src: 'S2', dst: 'WH1', is_alt: true, share: 0.3 })
  })

  it('rejects incomplete or unexpected network payloads instead of using mock fallback data', () => {
    expect(() => parseDemoNetwork({ nodes: [], edges: [] })).toThrow(ApiError)
  })
})

describe('simulation API client', () => {
  it('posts the backend network and failed node IDs and returns the real result shape', async () => {
    const result = {
      failed_nodes: ['S1'], directly_impacted_nodes: ['WH1'], second_order_impacted_nodes: ['ST1'],
      third_order_impacted_nodes: [], further_impacted_nodes: [], all_impacted_nodes: ['ST1', 'WH1'],
      overloaded_nodes: [], critical_shortage_nodes: ['ST1'], bottleneck_node: 'ST1',
      first_predicted_stockout_time_h: 4, propagation_rounds: 2, impact_score: 0.31, severity: 'high',
      round_snapshots: [], node_impacts: {}, recovery_estimate_h: 24, intervention: 'none',
      intervention_cost: 0, reasoning: ['Supply loss propagated'],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }))

    await expect(simulateNetwork(demoNetworkFixture, ['S1'])).resolves.toEqual(result)
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/simulate$/), expect.objectContaining({
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ network: demoNetworkFixture, failed_nodes: ['S1'] }),
    }))
  })

  it('surfaces backend validation errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Unknown failed node(s): BAD' }), { status: 422 }))
    await expect(simulateNetwork(demoNetworkFixture, ['BAD'])).rejects.toThrow('Unknown failed node(s): BAD')
  })
})

describe('intervention comparison API client', () => {
  it('posts the latest scenario network and failure IDs to /compare and validates the ranking', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(demoInterventionComparison), { status: 200 }))

    await expect(compareNetworkStrategies(demoNetworkFixture, ['S1'])).resolves.toEqual(demoInterventionComparison)
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/compare$/), expect.objectContaining({
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ network: demoNetworkFixture, failed_nodes: ['S1'] }),
    }))
  })

  it('surfaces backend validation and malformed response errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Unknown failed node(s): BAD' }), { status: 422 }))
    await expect(compareNetworkStrategies(demoNetworkFixture, ['BAD'])).rejects.toThrow('Unknown failed node(s): BAD')

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ scenarios: {} }), { status: 200 }))
    await expect(compareNetworkStrategies(demoNetworkFixture, ['S1'])).rejects.toThrow('unexpected shape')
  })
})
