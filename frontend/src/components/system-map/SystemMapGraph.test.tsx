import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { SupplyNetwork } from '../../api/types'
import { demoNetworkFixture } from '../../test/demoNetwork'
import { SystemMapGraph } from './SystemMapGraph'

vi.mock('@xyflow/react', async () => {
  const ReactModule = await import('react')
  return {
    BackgroundVariant: { Dots: 'dots' },
    MarkerType: { ArrowClosed: 'arrowclosed' },
    Background: () => null,
    Controls: () => null,
    Handle: () => null,
    Position: { Left: 'left', Right: 'right' },
    BaseEdge: () => null,
    EdgeLabelRenderer: ({ children }: { children: React.ReactNode }) => children,
    getBezierPath: () => ['', 0, 0],
    ReactFlow: ({ nodes, edges, onNodeClick, onPaneClick, children }: {
      nodes: { id: string }[]
      edges: { id: string }[]
      onNodeClick: (event: unknown, node: { id: string }) => void
      onPaneClick: () => void
      children: React.ReactNode
    }) => ReactModule.createElement('div', { 'data-testid': 'flow', 'data-node-count': nodes.length, 'data-edge-count': edges.length },
      ...nodes.map((node) => ReactModule.createElement('button', {
        key: node.id, onClick: (event: unknown) => onNodeClick(event, node),
      }, node.id)),
      ReactModule.createElement('button', { onClick: onPaneClick }, 'clear canvas'), children),
  }
})

describe('SystemMapGraph', () => {
  it('maps all backend facilities and routes and forwards node selection', () => {
    const selected = vi.fn()
    render(<SystemMapGraph network={demoNetworkFixture as SupplyNetwork} selectedNodeId={null} onSelectNode={selected} />)
    expect(screen.getByTestId('flow')).toHaveAttribute('data-node-count', '12')
    expect(screen.getByTestId('flow')).toHaveAttribute('data-edge-count', '16')
    fireEvent.click(screen.getByRole('button', { name: 'WH2' }))
    expect(selected).toHaveBeenCalledWith('WH2')
    fireEvent.click(screen.getByRole('button', { name: 'clear canvas' }))
    expect(selected).toHaveBeenLastCalledWith(null)
  })
})
