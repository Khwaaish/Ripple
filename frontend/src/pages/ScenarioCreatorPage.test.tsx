import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchDemoNetwork, simulateNetwork } from '../api/client'
import type { SimulationResult } from '../api/types'
import { demoNetworkFixture } from '../test/demoNetwork'
import { ScenarioCreatorPage } from './ScenarioCreatorPage'

vi.mock('../api/client', () => ({ fetchDemoNetwork: vi.fn(), simulateNetwork: vi.fn() }))

const result: SimulationResult = {
  failed_nodes: ['S1'], directly_impacted_nodes: ['WH1'], second_order_impacted_nodes: ['ST1'],
  third_order_impacted_nodes: [], further_impacted_nodes: [], all_impacted_nodes: ['ST1', 'WH1'],
  overloaded_nodes: [], critical_shortage_nodes: ['ST1'], bottleneck_node: 'ST1',
  first_predicted_stockout_time_h: 12, propagation_rounds: 2, impact_score: 0.315, severity: 'high',
  round_snapshots: [], node_impacts: {}, recovery_estimate_h: 24, intervention: 'none',
  intervention_cost: 0, reasoning: ['Cascade propagated from S1'],
}

describe('ScenarioCreatorPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchDemoNetwork).mockResolvedValue(demoNetworkFixture)
  })

  it('loads API facilities, supports selection and removal, submits, and shows backend results', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateNetwork).mockResolvedValue(result)
    render(<ScenarioCreatorPage />)

    expect(await screen.findByText('12 facilities')).toBeInTheDocument()
    const runButton = screen.getByRole('button', { name: 'Run simulation' })
    expect(runButton).toBeDisabled()

    const checkbox = screen.getByRole('checkbox', { name: 'Fail S1, Supplier' })
    await user.click(checkbox)
    expect(checkbox).toBeChecked()
    expect(screen.getByRole('button', { name: 'Remove S1' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Remove S1' }))
    expect(checkbox).not.toBeChecked()
    expect(runButton).toBeDisabled()

    await user.click(checkbox)
    await user.click(runButton)
    await waitFor(() => expect(simulateNetwork).toHaveBeenCalledWith(demoNetworkFixture, ['S1']))
    expect(await screen.findByRole('heading', { name: 'Cascade results' })).toBeInTheDocument()
    expect(screen.getByText('high severity')).toBeInTheDocument()
    expect(screen.getByText('0.315')).toBeInTheDocument()
    expect(screen.getByText('12 h')).toBeInTheDocument()
    expect(screen.getAllByText('ST1', { selector: 'span' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Cascade propagated from S1')).toBeInTheDocument()
  })

  it('shows API errors and handles facilities load failures with retry', async () => {
    const user = userEvent.setup()
    vi.mocked(simulateNetwork).mockRejectedValue(new Error('Unknown failed node(s): S1'))
    const view = render(<ScenarioCreatorPage />)
    const checkbox = await screen.findByRole('checkbox', { name: 'Fail S1, Supplier' })
    await user.click(checkbox)
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unknown failed node(s): S1')

    view.unmount()
    vi.mocked(fetchDemoNetwork).mockRejectedValueOnce(new Error('Backend unavailable'))
    render(<ScenarioCreatorPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable')
    vi.mocked(fetchDemoNetwork).mockResolvedValueOnce(demoNetworkFixture)
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('12 facilities')).toBeInTheDocument()
  })
})
