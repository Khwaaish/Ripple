import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { noCascadeRun, supplierCascadeRun } from '../../test/cascadeRun'
import { CascadeVisualization } from './CascadeVisualization'

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  BackgroundVariant: { Dots: 'dots' },
  Controls: () => null,
  MarkerType: { ArrowClosed: 'arrowclosed' },
  ReactFlow: ({ nodes, children }: {
    nodes: { id: string; data: { cascadeState?: string; cascadeCurrent?: boolean } }[]
    children: React.ReactNode
  }) => React.createElement('div', { 'data-testid': 'cascade-flow' },
    ...nodes.map((node) => React.createElement('span', {
      key: node.id,
      'data-testid': `node-${node.id}`,
      'data-cascade-state': node.data.cascadeState,
      'data-current': node.data.cascadeCurrent ? 'true' : 'false',
    }, node.id)), children),
}))

describe('CascadeVisualization', () => {
  afterEach(cleanup)

  it('plays and seeks through the actual engine round snapshots', async () => {
    const user = userEvent.setup()
    render(<CascadeVisualization run={supplierCascadeRun} />)

    expect(screen.getByTestId('node-S1')).toHaveAttribute('data-cascade-state', 'failed')
    expect(screen.getByTestId('node-WH1')).toHaveAttribute('data-cascade-state', 'unaffected')
    expect(screen.getByRole('button', { name: /Round 1/ })).toHaveTextContent('2 impacted')
    expect(screen.getByRole('button', { name: /Round 2/ })).toHaveTextContent('5 impacted')
    expect(screen.getByRole('button', { name: /Round 3/ })).toHaveTextContent('No new impacts')

    await user.click(screen.getByRole('button', { name: 'Play cascade' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Round 1/ })).toHaveAttribute('aria-pressed', 'true'), { timeout: 1800 })
    expect(screen.getByTestId('node-WH1')).toHaveAttribute('data-cascade-state', 'direct')
    expect(screen.getByTestId('node-WH1')).toHaveAttribute('data-current', 'true')
    expect(screen.getByTestId('node-ST1')).toHaveAttribute('data-cascade-state', 'unaffected')
    await user.click(screen.getByRole('button', { name: 'Pause cascade' }))

    await user.click(screen.getByRole('button', { name: /Round 2/ }))
    expect(screen.getByTestId('node-ST1')).toHaveAttribute('data-cascade-state', 'second')
    expect(screen.getByTestId('node-ST1')).toHaveAttribute('data-current', 'true')
    expect(screen.getByRole('heading', { name: 'Propagation round 2' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Round 3/ }))
    expect(screen.getByText('No new facilities were impacted in this round.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Replay cascade from start' }))
    expect(screen.getByRole('button', { name: /Initial/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('node-WH1')).toHaveAttribute('data-cascade-state', 'unaffected')
  })

  it('shows no-cascade state and disables playback when the engine reported no impacts', () => {
    render(<CascadeVisualization run={noCascadeRun} />)
    expect(screen.getByRole('status')).toHaveTextContent('No cascade propagated beyond the initially failed facilities.')
    expect(screen.getByRole('button', { name: 'Play cascade' })).toBeDisabled()
    expect(screen.getByTestId('node-ST1')).toHaveAttribute('data-cascade-state', 'failed')
  })
})
