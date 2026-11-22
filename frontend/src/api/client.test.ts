import { describe, expect, it } from 'vitest'
import { ApiError, parseDemoNetwork } from './client'
import { demoNetworkFixture } from '../test/demoNetwork'

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
