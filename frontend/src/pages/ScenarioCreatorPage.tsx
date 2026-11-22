import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, LoaderCircle, Play, RefreshCw, X } from 'lucide-react'
import { fetchDemoNetwork, simulateNetwork } from '../api/client'
import type { FacilityType, ScenarioRun, SimulationResult, SupplyNetwork } from '../api/types'
import { SectionHeading } from '../components/SectionHeading'
import type { SectionId } from '../types'

const typeLabel: Record<FacilityType, string> = {
  supplier: 'Supplier',
  warehouse: 'Warehouse',
  store: 'Store',
}

const typeTone: Record<FacilityType, string> = {
  supplier: 'border-sky-300/20 bg-sky-300/[.06] text-sky-200',
  warehouse: 'border-mint/20 bg-mint/[.06] text-mint',
  store: 'border-violet-300/20 bg-violet-300/[.06] text-violet-200',
}

function ResultMetric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <div className="rounded-lg border border-line bg-[#0d1117] p-3.5">
    <p className="text-[10px] font-medium uppercase tracking-[.1em] text-slate-600">{label}</p>
    <p className="mt-1.5 break-words text-sm font-semibold text-slate-100">{value}</p>
    {detail && <p className="mt-1 text-[10px] text-slate-500">{detail}</p>}
  </div>
}

function NodeList({ label, nodes }: { label: string; nodes: string[] }) {
  return <div>
    <div className="flex items-center justify-between gap-3">
      <p className="text-xs font-medium text-slate-300">{label}</p>
      <span className="rounded border border-line bg-[#0d1117] px-1.5 py-0.5 text-[10px] text-slate-500">{nodes.length}</span>
    </div>
    {nodes.length ? <div className="mt-2 flex flex-wrap gap-1.5">{nodes.map((node) => <span key={node} className="rounded-md border border-line bg-[#0d1117] px-2 py-1 font-mono text-[10px] text-slate-300">{node}</span>)}</div>
      : <p className="mt-2 text-[11px] text-slate-600">None</p>}
  </div>
}

function SimulationSummary({ result }: { result: SimulationResult }) {
  const cascadeGroups = [
    ['Direct impacts', result.directly_impacted_nodes],
    ['Second order', result.second_order_impacted_nodes],
    ['Third order', result.third_order_impacted_nodes],
    ['Further impacts', result.further_impacted_nodes],
  ] as const

  return <section className="panel-card p-5 sm:p-6" aria-labelledby="simulation-results-title" aria-live="polite">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="flex items-center gap-2"><span className="status-dot status-dot-green" /><p className="text-[10px] font-medium uppercase tracking-[.14em] text-mint">Simulation complete</p></div><h3 id="simulation-results-title" className="mt-2 text-base font-semibold text-slate-100">Cascade results</h3><p className="mt-1 text-xs text-slate-500">Calculated by the Ripple simulation API for {result.failed_nodes.join(', ')}.</p></div>
      <span className="rounded-md border border-amber-300/20 bg-amber-300/[.07] px-2.5 py-1 text-xs font-semibold capitalize text-amber-200">{result.severity} severity</span>
    </div>
    <div className="mt-5 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
      <ResultMetric label="Impact score" value={result.impact_score.toFixed(3)} detail="Weighted unmet demand score" />
      <ResultMetric label="Affected facilities" value={String(result.all_impacted_nodes.length)} detail="Excludes failed facilities" />
      <ResultMetric label="Cascade rounds" value={String(result.propagation_rounds)} />
      <ResultMetric label="First predicted stockout" value={result.first_predicted_stockout_time_h === null ? 'None' : `${result.first_predicted_stockout_time_h} h`} />
      <ResultMetric label="Bottleneck" value={result.bottleneck_node ?? 'None'} />
      <ResultMetric label="Recovery estimate" value={`${result.recovery_estimate_h} h`} />
      <ResultMetric label="Critical shortages" value={String(result.critical_shortage_nodes.length)} detail={result.critical_shortage_nodes.join(', ') || 'None'} />
      <ResultMetric label="Overloaded facilities" value={String(result.overloaded_nodes.length)} detail={result.overloaded_nodes.join(', ') || 'None'} />
    </div>
    <div className="mt-5 grid gap-5 lg:grid-cols-2">
      <div className="space-y-4">
        <p className="text-xs font-semibold text-slate-200">Affected nodes by cascade order</p>
        {cascadeGroups.map(([label, nodes]) => <NodeList key={label} label={label} nodes={nodes} />)}
      </div>
      <div className="space-y-4">
        <NodeList label="All impacted nodes" nodes={result.all_impacted_nodes} />
        {result.reasoning.length > 0 && <div><p className="text-xs font-medium text-slate-300">Engine notes</p><ul className="mt-2 space-y-1.5">{result.reasoning.map((reason, index) => <li key={`${index}-${reason}`} className="text-[11px] leading-relaxed text-slate-500">{reason}</li>)}</ul></div>}
      </div>
    </div>
  </section>
}

export function ScenarioCreatorPage({ onScenarioRunChange, onNavigate }: {
  onScenarioRunChange?: (run: ScenarioRun | null) => void
  onNavigate?: (section: SectionId) => void
} = {}) {
  const [network, setNetwork] = useState<SupplyNetwork | null>(null)
  const [selectedNodes, setSelectedNodes] = useState<string[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [simulationError, setSimulationError] = useState<string | null>(null)
  const [loadingNetwork, setLoadingNetwork] = useState(true)
  const [running, setRunning] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
  const [result, setResult] = useState<SimulationResult | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoadingNetwork(true)
    setLoadError(null)
    fetchDemoNetwork(controller.signal)
      .then((data) => {
        setNetwork(data)
        setSelectedNodes((current) => current.filter((id) => data.nodes.some((node) => node.id === id)))
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setNetwork(null)
        setSelectedNodes([])
        setLoadError(error instanceof Error ? error.message : 'Could not load the facility network.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoadingNetwork(false) })
    return () => controller.abort()
  }, [retryKey])

  const selectedSet = useMemo(() => new Set(selectedNodes), [selectedNodes])
  const updateSelection = useCallback((nodeId: string, checked: boolean) => {
    setSelectedNodes((current) => checked
      ? current.includes(nodeId) ? current : [...current, nodeId]
      : current.filter((id) => id !== nodeId))
    setSimulationError(null)
    setResult(null)
    onScenarioRunChange?.(null)
  }, [onScenarioRunChange])

  async function submitScenario(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!network) return
    const validIds = new Set(network.nodes.map((node) => node.id))
    const failedNodes = [...new Set(selectedNodes)].filter((id) => validIds.has(id))
    if (!failedNodes.length) {
      setSimulationError('Select at least one facility from the loaded network.')
      return
    }
    setRunning(true)
    setSimulationError(null)
    setResult(null)
    onScenarioRunChange?.(null)
    try {
      const nextResult = await simulateNetwork(network, failedNodes)
      setResult(nextResult)
      onScenarioRunChange?.({ network, result: nextResult })
    } catch (error) {
      setSimulationError(error instanceof Error ? error.message : 'The simulation could not be completed.')
    } finally {
      setRunning(false)
    }
  }

  return <div className="space-y-5 pb-10">
    <SectionHeading title="Scenario creator" description="Select facilities to fail and run a deterministic cascade simulation." action={result && onNavigate ? <button type="button" className="button-secondary" onClick={() => onNavigate('Ripple Simulation')}>View cascade animation <Play size={13} /></button> : undefined} />

    <form className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,.72fr)]" onSubmit={submitScenario}>
      <section className="panel-card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="text-[10px] font-medium uppercase tracking-[.14em] text-mint">SCENARIO INPUT</p><h3 className="mt-2 text-base font-semibold text-slate-100">Choose failed facilities</h3><p className="mt-1 text-xs leading-relaxed text-slate-500">Select one or more nodes in the live demo network. The simulator uses node IDs; no unsupported timing or disruption parameters are sent.</p></div>
          <div className="rounded-md border border-line bg-[#0d1117] px-2.5 py-1.5 text-[10px] text-slate-500">{network ? `${network.nodes.length} facilities` : 'Network pending'}</div>
        </div>

        {loadingNetwork && <div className="mt-6 flex min-h-40 items-center justify-center gap-2 text-xs text-slate-400" role="status"><LoaderCircle size={15} className="animate-spin text-mint" /> Loading facilities from Ripple API…</div>}
        {!loadingNetwork && loadError && <div className="mt-5 rounded-lg border border-rose-300/15 bg-rose-300/[.05] p-4" role="alert"><div className="flex gap-2 text-rose-200"><AlertTriangle size={15} className="mt-0.5 shrink-0" /><div><p className="text-xs font-medium">Couldn’t load facilities</p><p className="mt-1 text-[11px] leading-relaxed text-rose-200/70">{loadError}</p></div></div><button type="button" onClick={() => setRetryKey((key) => key + 1)} className="button-secondary mt-3"><RefreshCw size={13} /> Retry</button></div>}

        {!loadingNetwork && !loadError && network && <>
          <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {network.nodes.map((node) => <label key={node.id} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${selectedSet.has(node.id) ? 'border-mint/30 bg-mint/[.045]' : 'border-line bg-[#0d1117] hover:border-slate-600'}`}>
              <input type="checkbox" checked={selectedSet.has(node.id)} onChange={(event) => updateSelection(node.id, event.target.checked)} className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-emerald-400" aria-label={`Fail ${node.id}, ${typeLabel[node.type]}`} />
              <span className="min-w-0 flex-1"><span className="block truncate font-mono text-xs font-semibold text-slate-100">{node.id}</span><span className="mt-1 block text-[10px] text-slate-500">Facility ID</span></span>
              <span className={`rounded border px-1.5 py-1 text-[9px] ${typeTone[node.type]}`}>{typeLabel[node.type]}</span>
            </label>)}
          </div>

          <div className="mt-5 border-t border-line pt-4">
            <div className="flex items-center justify-between gap-2"><p className="text-xs font-medium text-slate-300">Failed facilities</p><span className="text-[10px] text-slate-600">{selectedNodes.length} selected</span></div>
            {selectedNodes.length ? <div className="mt-2.5 flex flex-wrap gap-2">{selectedNodes.map((id) => {
              const node = network.nodes.find((item) => item.id === id)
              if (!node) return null
              return <span key={id} className="inline-flex items-center gap-2 rounded-md border border-mint/20 bg-mint/[.05] px-2 py-1.5"><span className="font-mono text-[10px] text-slate-200">{id}</span><span className="text-[9px] text-slate-500">{typeLabel[node.type]}</span><button type="button" onClick={() => updateSelection(id, false)} aria-label={`Remove ${id}`} className="text-slate-500 transition hover:text-rose-300"><X size={12} /></button></span>
            })}</div> : <p className="mt-2 text-[11px] text-slate-600">No facilities selected. Choose at least one above.</p>}
          </div>
        </>}

        {simulationError && <p className="mt-4 rounded-lg border border-rose-300/15 bg-rose-300/[.05] px-3 py-2.5 text-xs leading-relaxed text-rose-200" role="alert"><AlertTriangle size={14} className="mr-2 inline align-[-2px]" />{simulationError}</p>}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <p className="text-[10px] text-slate-600">The network is loaded directly from the backend. No mock scenario results are used.</p>
          <button type="submit" className="button-primary" disabled={loadingNetwork || Boolean(loadError) || !network || selectedNodes.length === 0 || running}>
            {running ? <LoaderCircle size={14} className="animate-spin" /> : <Play size={14} />}{running ? 'Running simulation…' : 'Run simulation'}
          </button>
        </div>
      </section>

      <aside className="space-y-4">
        <section className="panel-card p-5"><div className="flex items-center gap-2"><span className="icon-tile icon-mint"><Check size={15} /></span><h3 className="text-sm font-semibold text-slate-200">Request preview</h3></div><p className="mt-3 text-[11px] leading-relaxed text-slate-500">The backend receives the loaded network and selected failed node IDs.</p><pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-[#0d1117] p-3 text-[10px] leading-relaxed text-slate-400">{JSON.stringify({ failed_nodes: selectedNodes }, null, 2)}</pre><p className="mt-2 font-mono text-[9px] text-slate-600">POST /simulate</p></section>
        <section className="rounded-xl border border-sky-300/10 bg-gradient-to-br from-sky-300/[.06] to-transparent p-5"><p className="text-[10px] font-medium uppercase tracking-[.12em] text-sky-200/80">Network inputs</p><p className="mt-2 text-xs font-medium text-slate-200">Backend-supported parameters only</p><p className="mt-1 text-[11px] leading-relaxed text-slate-500">Failure selection is based on real node IDs and types. Duration, timing, and event profiles are not part of this API request.</p></section>
      </aside>
    </form>

    {running && <section className="panel-card flex items-center gap-3 p-5" role="status"><LoaderCircle size={17} className="animate-spin text-mint" /><div><p className="text-xs font-medium text-slate-200">Running cascade simulation</p><p className="mt-1 text-[10px] text-slate-500">Waiting for the Ripple backend response…</p></div></section>}
    {result && <SimulationSummary result={result} />}
  </div>
}
