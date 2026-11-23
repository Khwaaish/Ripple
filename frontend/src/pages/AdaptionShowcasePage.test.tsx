import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { AdaptionShowcasePage } from './AdaptionShowcasePage'

describe('Adaption Showcase', () => {
  afterEach(cleanup)

  it('shows the supplied training configuration and labels platform win rates honestly', () => {
    render(<AdaptionShowcasePage />)

    expect(screen.getByRole('heading', { name: 'Adaption showcase' })).toBeInTheDocument()
    expect(screen.getAllByText('Gemma 3 4B PT').length).toBeGreaterThan(0)
    expect(screen.getByText('2,000 train')).toBeInTheDocument()
    expect(screen.getByText('300 held out')).toBeInTheDocument()
    expect(screen.getByText('PLATFORM-REPORTED TRAINING WIN RATES')).toBeInTheDocument()
    expect(screen.getByText('12%')).toBeInTheDocument()
    expect(screen.getByText('88%')).toBeInTheDocument()
    expect(screen.getByText('+76 percentage points')).toBeInTheDocument()
    expect(screen.getByText(/not held-out accuracy/i)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Inference validation in progress')
    expect(screen.getByText('184')).toBeInTheDocument()
    expect(screen.getByText('32')).toBeInTheDocument()
    expect(screen.getByText('64')).toBeInTheDocument()
  })

  it('shows every step in the adaptation-to-validation pipeline', () => {
    render(<AdaptionShowcasePage />)

    for (const step of [
      'Engine-labeled data',
      'Gemma 3 4B PT',
      'LoRA adaptation',
      'Ripple predictions',
      'Simulation validation',
    ]) {
      expect(screen.getAllByText(step).length).toBeGreaterThan(0)
    }
    expect(screen.getByText(/no held-out accuracy or successful prediction claims/i)).toBeInTheDocument()
  })
})
