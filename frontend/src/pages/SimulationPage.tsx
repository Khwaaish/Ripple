import { Activity, ArrowRight, Layers3, ShieldAlert } from 'lucide-react'
import type { ScenarioRun } from '../api/types'
import { CascadeVisualization } from '../components/simulation/CascadeVisualization'
import { SectionHeading } from '../components/SectionHeading'
import type { SectionId } from '../types'

export function SimulationPage({ scenarioRun, onNavigate }: {
  scenarioRun: ScenarioRun | null
  onNavigate: (section: SectionId) => void
}) {
  if (!scenarioRun) {
    return <div className="space-y-5 pb-10">
      <SectionHeading title="Ripple simulation" description="Watch a real engine run propagate through the supply network." />
      <section className="panel-card flex min-h-[360px] flex-col items-center justify-center p-8 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-mint/10 bg-mint/[.06] text-mint"><Activity size={20} /></span>
        <h3 className="mt-4 text-base font-semibold text-slate-100">No scenario result to play yet</h3>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">Create a scenario and run it through the simulation API. Its actual propagation rounds will appear here.</p>
        <button className="button-primary mt-5" onClick={() => onNavigate('Scenario Creator')}>Open Scenario Creator <ArrowRight size={14} /></button>
      </section>
    </div>
  }

  const { result, network } = scenarioRun
  const roundCount = result.round_snapshots.length
  return <div className="space-y-5 pb-10">
    <SectionHeading title="Ripple simulation" description="Replay the deterministic cascade returned by the Ripple engine." action={<span className="inline-flex items-center gap-2 rounded-md border border-mint/15 bg-mint/[.05] px-2.5 py-1.5 text-[10px] text-mint"><span className="status-dot status-dot-green" /> Engine result loaded</span>} />
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Simulation summary">
      <div className="map-summary-card"><span className="map-summary-icon text-rose-300"><ShieldAlert size={15} /></span><div><p className="map-summary-value">{result.failed_nodes.join(', ')}</p><p className="map-summary-label">Initially failed</p></div></div>
      <div className="map-summary-card"><span className="map-summary-icon text-amber-200"><Activity size={15} /></span><div><p className="map-summary-value capitalize">{result.severity}</p><p className="map-summary-label">{(result.impact_score * 100).toFixed(1)}% impact score</p></div></div>
      <div className="map-summary-card"><span className="map-summary-icon text-sky-300"><Layers3 size={15} /></span><div><p className="map-summary-value">{roundCount} rounds</p><p className="map-summary-label">From engine round snapshots</p></div></div>
      <div className="map-summary-card"><span className="map-summary-icon text-violet-300"><Activity size={15} /></span><div><p className="map-summary-value">{result.all_impacted_nodes.length} / {network.nodes.length}</p><p className="map-summary-label">Impacted / total facilities</p></div></div>
    </section>
    <CascadeVisualization run={scenarioRun} />
  </div>
}
