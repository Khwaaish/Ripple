import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowRight, Check, CircleHelp, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react'
import { compareNetworkStrategies } from '../api/client'
import type { InterventionComparison, InterventionStrategy, ScenarioRun } from '../api/types'
import { SectionHeading } from '../components/SectionHeading'
import type { SectionId } from '../types'

const strategyNames: Record<InterventionStrategy, string> = {
  none: 'Baseline · no intervention',
  reroute: 'Reroute',
  backup_supplier: 'Backup supplier',
  prioritize: 'Prioritize critical destinations',
}

const strategyDetails: Record<InterventionStrategy, string> = {
  none: 'Reference outcome with no mitigation applied.',
  reroute: 'Uses available alternate incoming supply routes.',
  backup_supplier: 'Models bounded temporary backup supply after its configured delay.',
  prioritize: 'Uses alternate routes while allocating flow to critical destinations first.',
}

function reductionLabel(strategy: InterventionStrategy, comparison: InterventionComparison): string {
  const baseline = comparison.scenarios.none.impact_score
  const ratio = comparison.scenarios[strategy].relative_impact_vs_baseline
  if (strategy === 'none' || baseline === 0 || ratio === null) return '—'
  const reduction = (1 - ratio) * 100
  if (Math.abs(reduction) < 0.05) return 'No change'
  return reduction > 0 ? `${reduction.toFixed(1)}% lower` : `${Math.abs(reduction).toFixed(1)}% higher`
}

function StrategyComparison({ comparison }: { comparison: InterventionComparison }) {
  const rank = new Map(comparison.ranking.map((strategy, index) => [strategy, index + 1]))
  const rowOrder: InterventionStrategy[] = ['none', ...comparison.ranking.filter((strategy) => strategy !== 'none')]
  const best = comparison.recommended_strategy
  const baselineScore = comparison.scenarios.none.impact_score

  return <div className="space-y-4">
    <section className="rounded-xl border border-mint/15 bg-gradient-to-br from-mint/[.08] to-transparent p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-3"><span className="icon-tile icon-mint"><ShieldCheck size={17} /></span><div><p className="text-[10px] font-medium uppercase tracking-[.13em] text-mint">Engine recommendation · rank 1</p><h3 className="mt-1.5 text-base font-semibold text-slate-100">{strategyNames[best]}</h3><p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-400">{comparison.recommendation_reason}</p></div></div>
        <span className="rounded-full border border-mint/20 bg-mint/[.08] px-2.5 py-1 text-[10px] font-semibold text-mint">Best by API ranking</span>
      </div>
      {best !== 'none' && <p className="ml-12 mt-3 text-[10px] text-slate-500">{strategyDetails[best]} Result metrics and tie-breaks are shown in the comparison below.</p>}
      {best === 'none' && <p className="ml-12 mt-3 text-[10px] text-slate-500">The API ranked the baseline first for this scenario; no intervention outperformed it under the engine’s ranking.</p>}
    </section>

    {baselineScore === 0 && <p className="rounded-lg border border-slate-700/70 bg-[#0d1117] px-3 py-2.5 text-[11px] text-slate-400" role="status">Baseline impact is zero, so relative impact reduction is not meaningful for this scenario.</p>}

    <section className="panel-card overflow-hidden">
      <div className="border-b border-line px-5 py-4 sm:px-6"><h3 className="text-sm font-semibold text-slate-200">Baseline and intervention outcomes</h3><p className="mt-1 text-[11px] text-slate-500">Strategies are ordered from the API ranking after the baseline reference row. Lower impact score ranks better.</p></div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left">
          <thead><tr className="border-b border-line bg-white/[.015] text-[9px] uppercase tracking-[.1em] text-slate-600"><th className="px-4 py-3 font-medium">Rank</th><th className="px-4 py-3 font-medium">Strategy</th><th className="px-4 py-3 font-medium">Impact score</th><th className="px-4 py-3 font-medium">Vs baseline</th><th className="px-4 py-3 font-medium">Disrupted</th><th className="px-4 py-3 font-medium">Critical shortages</th><th className="px-4 py-3 font-medium">Overloaded</th><th className="px-4 py-3 font-medium">Recovery</th><th className="px-4 py-3 font-medium">Cost</th></tr></thead>
          <tbody className="divide-y divide-line/70">
            {rowOrder.map((strategy) => {
              const metrics = comparison.scenarios[strategy]
              const recommended = strategy === best
              return <tr key={strategy} className={`${recommended ? 'bg-mint/[.035]' : ''} ${strategy === 'none' ? 'bg-white/[.01]' : ''}`}>
                <td className="px-4 py-4"><span className={`inline-flex h-6 min-w-6 items-center justify-center rounded-md border px-1.5 text-[10px] font-semibold ${recommended ? 'border-mint/20 bg-mint/[.08] text-mint' : 'border-line bg-[#0d1117] text-slate-500'}`}>{rank.get(strategy)}</span></td>
                <td className="px-4 py-4"><div className="flex items-center gap-2"><p className="whitespace-nowrap text-xs font-semibold text-slate-200">{strategyNames[strategy]}</p>{recommended && <span className="rounded border border-mint/15 px-1.5 py-0.5 text-[8px] font-medium text-mint">TOP</span>}</div><p className="mt-1 max-w-[210px] text-[9px] leading-relaxed text-slate-600">{strategyDetails[strategy]}</p></td>
                <td className="px-4 py-4"><div className="flex items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-800"><div className={`h-full rounded-full ${recommended ? 'bg-mint' : 'bg-sky-300/60'}`} style={{ width: `${Math.max(0, Math.min(100, metrics.impact_score * 100))}%` }} /></div><span className="font-mono text-[11px] text-slate-300">{metrics.impact_score.toFixed(3)}</span></div></td>
                <td className={`whitespace-nowrap px-4 py-4 text-[11px] font-medium ${reductionLabel(strategy, comparison).includes('lower') ? 'text-mint' : reductionLabel(strategy, comparison).includes('higher') ? 'text-amber-300' : 'text-slate-500'}`}>{reductionLabel(strategy, comparison)}</td>
                <td className="px-4 py-4"><span className="text-xs font-medium text-slate-300">{metrics.nodes_disrupted.length}</span><p className="mt-1 max-w-[110px] truncate text-[9px] text-slate-600" title={metrics.nodes_disrupted.join(', ')}>{metrics.nodes_disrupted.join(', ') || 'None'}</p></td>
                <td className="px-4 py-4"><span className="text-xs font-medium text-slate-300">{metrics.critical_shortages.length}</span><p className="mt-1 max-w-[110px] truncate text-[9px] text-slate-600" title={metrics.critical_shortages.join(', ')}>{metrics.critical_shortages.join(', ') || 'None'}</p></td>
                <td className="px-4 py-4"><span className="text-xs font-medium text-slate-300">{metrics.overloaded_nodes.length}</span><p className="mt-1 max-w-[100px] truncate text-[9px] text-slate-600" title={metrics.overloaded_nodes.join(', ')}>{metrics.overloaded_nodes.join(', ') || 'None'}</p></td>
                <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-300">{metrics.estimated_recovery_time_h} h</td>
                <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-300">{metrics.intervention_cost.toFixed(2)}</td>
              </tr>
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-5 py-3 text-[9px] text-slate-600 sm:px-6"><span>Cost is shown as the engine-returned numeric value; no currency unit is specified by the API.</span><span>Severity is not included in the /compare response.</span></div>
    </section>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {comparison.ranking.map((strategy, index) => <article key={strategy} className={`panel-card p-4 ${strategy === best ? 'border-mint/25' : ''}`}><div className="flex items-center justify-between gap-2"><p className="text-xs font-semibold text-slate-200">#{index + 1} {strategyNames[strategy]}</p>{strategy === best && <Check size={14} className="text-mint" />}</div><p className="mt-2 text-[10px] leading-relaxed text-slate-500">{comparison.scenarios[strategy].reasoning.join(' ') || 'No engine notes returned.'}</p></article>)}
    </section>
  </div>
}

export function InterventionCenterPage({ scenarioRun, onNavigate }: {
  scenarioRun: ScenarioRun | null
  onNavigate: (section: SectionId) => void
}) {
  const [comparison, setComparison] = useState<InterventionComparison | null>(null)
  const [loading, setLoading] = useState(Boolean(scenarioRun))
  const [error, setError] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    if (!scenarioRun) {
      setComparison(null)
      setLoading(false)
      setError(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setComparison(null)
    setError(null)
    compareNetworkStrategies(scenarioRun.network, scenarioRun.result.failed_nodes, controller.signal)
      .then(setComparison)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setError(reason instanceof Error ? reason.message : 'Could not compare intervention strategies.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [scenarioRun, retryKey])

  return <div className="space-y-5 pb-10">
    <SectionHeading title="Intervention center" description="Compare engine-modeled mitigation outcomes for the latest successful scenario." action={<span className="inline-flex items-center gap-2 rounded-md border border-line bg-[#0d1117] px-2.5 py-1.5 text-[10px] text-slate-500"><CircleHelp size={13} /> Deterministic strategy comparison</span>} />

    {!scenarioRun && <section className="panel-card flex min-h-[340px] flex-col items-center justify-center p-8 text-center"><span className="flex h-12 w-12 items-center justify-center rounded-xl border border-sky-300/10 bg-sky-300/[.06] text-sky-200"><ShieldCheck size={20} /></span><h3 className="mt-4 text-base font-semibold text-slate-100">Run a scenario before comparing strategies</h3><p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">The Intervention Center uses the network and failed facility IDs from the latest successful Scenario Creator run. It does not create a separate scenario.</p><button className="button-primary mt-5" onClick={() => onNavigate('Scenario Creator')}>Open Scenario Creator <ArrowRight size={14} /></button></section>}

    {scenarioRun && <>
      <section className="panel-card flex flex-wrap items-center justify-between gap-4 p-4 sm:px-5"><div><p className="text-[10px] font-medium uppercase tracking-[.12em] text-slate-600">Latest successful Scenario Creator run</p><p className="mt-1 text-xs font-semibold text-slate-200">{scenarioRun.result.failed_nodes.length} failed {scenarioRun.result.failed_nodes.length === 1 ? 'facility' : 'facilities'} <span className="mx-1 text-slate-700">·</span> {scenarioRun.network.nodes.length} network facilities</p><div className="mt-2 flex flex-wrap gap-1.5">{scenarioRun.result.failed_nodes.map((id) => { const facility = scenarioRun.network.nodes.find((node) => node.id === id); return <span key={id} className="rounded border border-rose-300/15 bg-rose-300/[.05] px-2 py-1 font-mono text-[10px] text-rose-200">{id}{facility ? ` · ${facility.type}` : ''}</span> })}</div></div><button className="button-secondary" onClick={() => setRetryKey((key) => key + 1)} disabled={loading || !scenarioRun}><RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh comparison</button></section>

      {loading && <section className="panel-card flex min-h-[260px] flex-col items-center justify-center p-6" role="status"><LoaderCircle size={20} className="animate-spin text-mint" /><p className="mt-3 text-sm font-medium text-slate-200">Comparing mitigation strategies</p><p className="mt-1 text-xs text-slate-600">Waiting for the /compare API response…</p></section>}
      {!loading && error && <section className="panel-card flex min-h-[260px] flex-col items-center justify-center p-8 text-center" role="alert"><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-rose-300/15 bg-rose-300/[.06] text-rose-200"><AlertTriangle size={18} /></span><h3 className="mt-4 text-sm font-semibold text-slate-100">Couldn’t compare strategies</h3><p className="mt-2 max-w-md text-xs leading-relaxed text-slate-500">{error}</p><button className="button-primary mt-4" onClick={() => setRetryKey((key) => key + 1)}><RefreshCw size={13} /> Retry comparison</button></section>}
      {!loading && !error && comparison && <StrategyComparison comparison={comparison} />}
    </>}
  </div>
}
