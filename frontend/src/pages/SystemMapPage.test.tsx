import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchDemoNetwork } from '../api/client'
import { demoNetworkFixture } from '../test/demoNetwork'
import { SystemMapPage } from './SystemMapPage'

vi.mock('../api/client', () => ({ fetchDemoNetwork: vi.fn() }))
vi.mock('../components/system-map/SystemMapGraph', () => ({
  SystemMapGraph: ({ network, selectedNodeId, onSelectNode }: {
    network: typeof demoNetworkFixture
    selectedNodeId: string | null
    onSelectNode: (nodeId: string | null) => void
  }) => React.createElement('div', { 'data-testid': 'mock-map', 'data-nodes': network.nodes.length, 'data-edges': network.edges.length },
    React.createElement('span', null, selectedNodeId ?? 'none'),
    React.createElement('button', { onClick: () => onSelectNode('WH1') }, 'Select WH1'),
    React.createElement('button', { onClick: () => onSelectNode(null) }, 'Clear map selection')),
}))

describe('SystemMapPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading state and then real-network counts and selected node details', async () => {
    let resolveNetwork!: (network: typeof demoNetworkFixture) => void
    vi.mocked(fetchDemoNetwork).mockReturnValue(new Promise((resolve) => { resolveNetwork = resolve }))
    render(<SystemMapPage />)
    expect(screen.getByText('Loading supply network')).toBeInTheDocument()
    await act(async () => resolveNetwork(demoNetworkFixture))
    expect(await screen.findByTestId('mock-map')).toHaveAttribute('data-nodes', '12')
    expect(screen.getByTestId('mock-map')).toHaveAttribute('data-edges', '16')
    expect(screen.getByText('Facility properties')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Select WH1' }))
    expect(screen.getByText('this facility → ST1')).toBeInTheDocument()
    expect(screen.getByText('this facility → ST2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear map selection' }))
    expect(screen.getByText('Select a facility')).toBeInTheDocument()
  })

  it('shows an API error and retries on user request', async () => {
    vi.mocked(fetchDemoNetwork)
      .mockRejectedValueOnce(new Error('Backend unavailable for test'))
      .mockResolvedValueOnce(demoNetworkFixture)
    render(<SystemMapPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable for test')
    fireEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
    await waitFor(() => expect(screen.getByTestId('mock-map')).toBeInTheDocument())
    expect(fetchDemoNetwork).toHaveBeenCalledTimes(2)
  })
})
