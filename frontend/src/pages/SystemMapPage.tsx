import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ArrowDown, Boxes, CircleHelp, LoaderCircle, RefreshCw, Wifi } from 'lucide-react'
import { fetchDemoNetwork } from '../api/client'
import type { SupplyNetwork } from '../api/types'
import { MapLegend } from '../components/system-map/MapLegend'
import { NodeDetailsPanel } from '../components/system-map/NodeDetailsPanel'
import { SystemMapGraph } from '../components/system-map/SystemMapGraph'

export function SystemMapPage() {
  const [network, setNetwork] = useState<SupplyNetwork | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchDemoNetwork(controller.signal)
      .then((result) => {
        setNetwork(result)
        setSelectedNodeId(result.nodes[0]?.id ?? null)
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setError(reason instanceof Error ? reason.message : 'Could not load the demo network.')
        setNetwork(null)
        setSelectedNodeId(null)
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [retryKey])

  const retry = useCallback(() => setRetryKey((value) => value + 1), [])
  const selectedNode = network?.nodes.find((node) => node.id === selectedNodeId) ?? null
  const criticalCount = network?.nodes.filter((node) => node.critical).length ?? 0
  const nodeTypes = network?.nodes.reduce((counts, node) => {
    counts[node.type] += 1
    return counts
  }, { supplier: 0, warehouse: 0, store: 0 })

  return <div className="space-y-5 pb-10">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[.14em] text-mint/80"><span className="status-dot status-dot-green" /> Live network data</div><h2 className="text-[23px] font-semibold tracking-tight text-slate-50">System map</h2><p className="mt-1 text-sm text-slate-500">Follow supply flow across facilities and inspect connected routes.</p></div>
      <button onClick={retry} disabled={loading} className="button-secondary disabled:cursor-wait disabled:opacity-50"><RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh network</button>
    </div>

    {loading && <section className="panel-card flex min-h-[490px] flex-col items-center justify-center p-6" role="status" aria-live="polite"><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-mint/10 bg-mint/[.06] text-mint"><LoaderCircle size={20} className="animate-spin" /></span><p className="mt-4 text-sm font-medium text-slate-200">Loading supply network</p><p className="mt-1 text-xs text-slate-600">Connecting to the Ripple demo network…</p><div className="mt-7 grid w-full max-w-xl gap-3 sm:grid-cols-3">{[0, 1, 2].map((column) => <div key={column} className="space-y-3">{[0, 1, 2].map((row) => <div key={row} className="h-12 animate-pulse rounded-lg border border-line bg-[#0d1117]" />)}</div>)}</div></section>}

    {!loading && error && <section className="panel-card flex min-h-[420px] flex-col items-center justify-center p-8 text-center" role="alert"><span className="flex h-12 w-12 items-center justify-center rounded-xl border border-rose-400/15 bg-rose-400/[.07] text-rose-300"><AlertTriangle size={20} /></span><h3 className="mt-4 text-base font-semibold text-slate-100">Couldn’t load the network</h3><p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">{error}</p><button onClick={retry} className="button-primary mt-5"><RefreshCw size={14} /> Retry connection</button><p className="mt-4 text-[10px] text-slate-700">The map does not substitute mock data when the API is unavailable.</p></section>}

    {!loading && !error && network && <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="map-summary-card"><span className="map-summary-icon text-mint"><Boxes size={15} /></span><div><p className="map-summary-value">{network.nodes.length}<span> facilities</span></p><p className="map-summary-label">Demo supply network</p></div></div>
        <div className="map-summary-card"><span className="map-summary-icon text-sky-300"><ArrowDown size={15} /></span><div><p className="map-summary-value">{network.edges.length}<span> routes</span></p><p className="map-summary-label">Directed supply connections</p></div></div>
        <div className="map-summary-card"><span className="map-summary-icon text-violet-300"><Boxes size={15} /></span><div><p className="map-summary-value">{nodeTypes?.supplier ?? 0} / {nodeTypes?.warehouse ?? 0} / {nodeTypes?.store ?? 0}</p><p className="map-summary-label">Suppliers / warehouses / stores</p></div></div>
        <div className="map-summary-card"><span className="map-summary-icon text-amber-300"><AlertTriangle size={15} /></span><div><p className="map-summary-value">{criticalCount}<span> critical</span></p><p className="map-summary-label">Flagged facilities</p></div></div>
      </section>
      <section className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_310px]">
        <article className="panel-card min-w-0 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3.5 sm:px-5"><div><div className="flex items-center gap-2"><h3 className="text-xs font-semibold text-slate-200">Supply flow</h3><span className="rounded border border-mint/10 bg-mint/[.05] px-1.5 py-0.5 text-[9px] text-mint">DEMO NETWORK</span></div><p className="mt-1 text-[10px] text-slate-600">Upstream suppliers <span className="mx-1">→</span> distribution <span className="mx-1">→</span> retail</p></div><span className="flex items-center gap-1.5 text-[10px] text-slate-500"><Wifi size={12} className="text-mint" /> Connected to API</span></div>
          <div className="border-b border-line/80 px-4 py-3 sm:px-5"><MapLegend /></div>
          <SystemMapGraph network={network} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} />
          <div className="flex items-center justify-between border-t border-line/80 px-4 py-2.5 text-[9px] text-slate-600 sm:px-5"><span>Click a facility to inspect its properties and routes.</span><span className="hidden items-center gap-1 sm:flex"><CircleHelp size={11} /> Scroll to zoom <span className="mx-1">·</span> Drag to pan</span></div>
        </article>
        <NodeDetailsPanel facility={selectedNode} edges={network.edges} onClear={() => setSelectedNodeId(null)} />
      </section>
    </>}
  </div>
}
