import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { compareNetworkStrategies } from '../api/client'
import { supplierCascadeRun } from '../test/cascadeRun'
import { demoInterventionComparison } from '../test/interventionComparison'
import { InterventionCenterPage } from './InterventionCenterPage'

vi.mock('../api/client', () => ({ compareNetworkStrategies: vi.fn() }))

describe('InterventionCenterPage', () => {
  afterEach(cleanup)
  beforeEach(() => vi.clearAllMocks())

  it('loads and displays API strategy ranking and metrics for the shared latest scenario', async () => {
    vi.mocked(compareNetworkStrategies).mockResolvedValue(demoInterventionComparison)
    render(<InterventionCenterPage scenarioRun={supplierCascadeRun} onNavigate={vi.fn()} />)

    expect(await screen.findByText('Engine recommendation · rank 1')).toBeInTheDocument()
    expect(compareNetworkStrategies).toHaveBeenCalledWith(supplierCascadeRun.network, ['S1'], expect.any(AbortSignal))
    expect(screen.getByText('Selected prioritize: lowest weighted impact, then recovery time, then intervention cost.')).toBeInTheDocument()
    expect(screen.getAllByText('31.2% lower')).toHaveLength(2)
    expect(screen.getByText('0.244')).toBeInTheDocument()
    expect(screen.getByText('0.236')).toBeInTheDocument()
    expect(screen.getAllByText('0.168')).toHaveLength(2)
    expect(screen.getByText('No intervention supply was applied')).toBeInTheDocument()
    expect(screen.getByText(/Severity is not included/)).toBeInTheDocument()
  })

  it('shows a useful no-scenario state with navigation to Scenario Creator', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<InterventionCenterPage scenarioRun={null} onNavigate={onNavigate} />)
    expect(screen.getByText('Run a scenario before comparing strategies')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open Scenario Creator' }))
    expect(onNavigate).toHaveBeenCalledWith('Scenario Creator')
    expect(compareNetworkStrategies).not.toHaveBeenCalled()
  })

  it('displays API errors and retries the latest run comparison', async () => {
    const user = userEvent.setup()
    vi.mocked(compareNetworkStrategies)
      .mockRejectedValueOnce(new Error('Comparison service unavailable'))
      .mockResolvedValueOnce(demoInterventionComparison)
    render(<InterventionCenterPage scenarioRun={supplierCascadeRun} onNavigate={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Comparison service unavailable')
    await user.click(screen.getByRole('button', { name: 'Retry comparison' }))
    await waitFor(() => expect(screen.getByText('Selected prioritize: lowest weighted impact, then recovery time, then intervention cost.')).toBeInTheDocument())
    expect(compareNetworkStrategies).toHaveBeenCalledTimes(2)
  })
})
