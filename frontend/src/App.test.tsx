import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ScenarioRun } from './api/types'
import { compareNetworkStrategies, fetchDemoNetwork, simulateNetwork } from './api/client'
import { supplierCascadeRun } from './test/cascadeRun'
import { demoNetworkFixture } from './test/demoNetwork'
import { demoInterventionComparison } from './test/interventionComparison'
import App from './App'

vi.mock('./api/client', () => ({ fetchDemoNetwork: vi.fn(), simulateNetwork: vi.fn(), compareNetworkStrategies: vi.fn() }))
vi.mock('./components/simulation/CascadeVisualization', () => ({
  CascadeVisualization: ({ run }: { run: ScenarioRun }) => React.createElement('div', { 'data-testid': 'scenario-round-count' }, String(run.result.round_snapshots.length)),
}))

describe('App scenario-to-simulation flow', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchDemoNetwork).mockResolvedValue(demoNetworkFixture)
    vi.mocked(simulateNetwork).mockResolvedValue(supplierCascadeRun.result)
    vi.mocked(compareNetworkStrategies).mockResolvedValue(demoInterventionComparison)
  })

  it('keeps the real scenario network and result when navigating to Ripple Simulation', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByTitle('Scenario Creator'))
    await screen.findByRole('checkbox', { name: 'Fail S1, Supplier' })
    await user.click(screen.getByRole('checkbox', { name: 'Fail S1, Supplier' }))
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    expect(await screen.findByRole('heading', { name: 'Cascade results' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'View cascade animation' }))
    expect(await screen.findByTestId('scenario-round-count')).toHaveTextContent('3')
    expect(screen.getByText('7 / 12')).toBeInTheDocument()
    expect(simulateNetwork).toHaveBeenCalledWith(demoNetworkFixture, ['S1'])
  })

  it('passes the latest successful scenario into Intervention Center', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByTitle('Scenario Creator'))
    await user.click(await screen.findByRole('checkbox', { name: 'Fail S1, Supplier' }))
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    await screen.findByRole('heading', { name: 'Cascade results' })

    await user.click(screen.getByTitle('Intervention Center'))
    expect(await screen.findByText('Engine recommendation · rank 1')).toBeInTheDocument()
    expect(compareNetworkStrategies).toHaveBeenCalledWith(demoNetworkFixture, ['S1'], expect.any(AbortSignal))
  })
})
