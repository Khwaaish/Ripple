import { useEffect, useMemo, useState } from 'react'
import { Background, BackgroundVariant, Controls, MarkerType, ReactFlow, type EdgeTypes, type NodeTypes } from '@xyflow/react'
import { Pause, Play, RotateCcw } from 'lucide-react'
import type { ScenarioRun } from '../../api/types'
import { FacilityNodeView } from '../system-map/FacilityNodeView'
import { SupplyEdgeView } from '../system-map/SupplyEdgeView'
import { nodePositions, spaceEdgeLabels } from '../system-map/SystemMapGraph'
import type { CascadeNodeState, FacilityFlowNode, SupplyFlowEdge } from '../system-map/types'

const nodeTypes: NodeTypes = { facility: FacilityNodeView }
const edgeTypes: EdgeTypes = { supply: SupplyEdgeView }
const NODE_WIDTH = 194
const NODE_HEIGHT = 90

const legend: { state: CascadeNodeState; label: string }[] = [
  { state: 'failed', label: 'Initially failed' },
  { state: 'direct', label: 'Direct impact' },
  { state: 'second', label: 'Second order' },
  { state: 'third', label: 'Third order' },
  { state: 'further', label: 'Further impact' },
  { state: 'unaffected', label: 'Unaffected' },
]

function facilityState(id: string, run: ScenarioRun, completedRounds: Set<number>): CascadeNodeState {
  if (run.result.failed_nodes.includes(id)) return 'failed'
  if (!run.result.round_snapshots.some((snapshot) => completedRounds.has(snapshot.round) && snapshot.newly_impacted.includes(id))) return 'unaffected'
  if (run.result.directly_impacted_nodes.includes(id)) return 'direct'
  if (run.result.second_order_impacted_nodes.includes(id)) return 'second'
  if (run.result.third_order_impacted_nodes.includes(id)) return 'third'
  if (run.result.further_impacted_nodes.includes(id)) return 'further'
  return 'impacted'
}

function CascadeGraph({ run, currentStep }: { run: ScenarioRun; currentStep: number }) {
  const positions = useMemo(() => nodePositions(run.network.nodes), [run.network.nodes])
  const offsets = useMemo(() => spaceEdgeLabels(run.network.edges, positions), [run.network.edges, positions])
  const completedRounds = useMemo(() => new Set(run.result.round_snapshots.slice(0, currentStep + 1).map((snapshot) => snapshot.round)), [run.result.round_snapshots, currentStep])
  const currentNodes = new Set(currentStep < 0 ? [] : run.result.round_snapshots[currentStep]?.newly_impacted ?? [])

  const nodes = useMemo<FacilityFlowNode[]>(() => run.network.nodes.map((facility) => {
    const cascadeState = facilityState(facility.id, run, completedRounds)
    return {
      id: facility.id,
      type: 'facility',
      position: positions.get(facility.id)!,
      data: { facility, selected: false, cascadeState, cascadeCurrent: currentNodes.has(facility.id) },
      draggable: false,
      selectable: false,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      style: { width: NODE_WIDTH, height: NODE_HEIGHT },
    }
  }), [run, positions, completedRounds, currentStep])

  const edges = useMemo<SupplyFlowEdge[]>(() => run.network.edges.map((supply) => ({
    id: `${supply.src}-${supply.dst}`,
    source: supply.src,
    target: supply.dst,
    type: 'supply',
    data: { supply, labelOffsetY: offsets.get(`${supply.src}->${supply.dst}`) ?? 0 },
    markerEnd: { type: MarkerType.ArrowClosed, color: supply.is_alt ? '#d9a86f' : '#65768a', width: 13, height: 13 },
    zIndex: supply.is_alt ? 0 : 1,
    ariaLabel: `Supply route ${supply.src} to ${supply.dst}`,
    selectable: false,
    focusable: false,
    style: { stroke: supply.is_alt ? '#d9a86f' : '#65768a', strokeDasharray: supply.is_alt ? '5 5' : undefined },
  })), [run.network.edges, offsets])

  return <div className="system-flow-canvas cascade-flow-canvas" role="application" aria-label="Animated supply chain cascade network">
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.13, minZoom: 0.45, maxZoom: 1.15 }}
      minZoom={0.4}
      maxZoom={1.5}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag
      zoomOnScroll
      zoomOnPinch
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#27313d" />
      <Controls showInteractive={false} position="bottom-left" />
    </ReactFlow>
  </div>
}

export function CascadeVisualization({ run }: { run: ScenarioRun }) {
  const [currentStep, setCurrentStep] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const snapshots = run.result.round_snapshots
  const hasCascade = run.result.all_impacted_nodes.length > 0
  const activeSnapshot = currentStep >= 0 ? snapshots[currentStep] : null
  const currentAffected = currentStep < 0 ? run.result.failed_nodes : activeSnapshot?.newly_impacted ?? []

  useEffect(() => {
    setCurrentStep(-1)
    setPlaying(false)
  }, [run])

  useEffect(() => {
    if (!playing) return
    if (currentStep >= snapshots.length - 1) {
      setPlaying(false)
      return
    }
    const timer = window.setTimeout(() => setCurrentStep((step) => step + 1), 1050)
    return () => window.clearTimeout(timer)
  }, [playing, currentStep, snapshots.length])

  function play() {
    if (!hasCascade || snapshots.length === 0) return
    if (currentStep >= snapshots.length - 1) setCurrentStep(-1)
    setPlaying(true)
  }

  function seek(step: number) {
    setPlaying(false)
    setCurrentStep(step)
  }

  return <section className="space-y-4" aria-label="Cascade playback">
    <div className="panel-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3.5 sm:px-5">
        <div><div className="flex flex-wrap items-center gap-2"><h3 className="text-xs font-semibold text-slate-200">Cascade propagation</h3><span className="rounded border border-rose-300/15 bg-rose-300/[.06] px-1.5 py-0.5 font-mono text-[9px] text-rose-200">FAILED: {run.result.failed_nodes.join(', ')}</span></div><p className="mt-1 text-[10px] text-slate-600">Round timing and affected nodes come directly from the simulation response.</p></div>
        <span className="rounded-md border border-line bg-[#0d1117] px-2.5 py-1.5 text-[10px] font-medium text-slate-400">{currentStep < 0 ? 'Initial disruption' : `Round ${activeSnapshot?.round ?? '—'} / ${snapshots.length}`}</span>
      </div>
      <CascadeGraph run={run} currentStep={currentStep} />
      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-line/80 px-4 py-3 sm:px-5" aria-label="Cascade node legend">
        {legend.map(({ state, label }) => <span key={state} className="inline-flex items-center gap-1.5 text-[9px] text-slate-500"><i className={`cascade-legend-dot cascade-${state}`} />{label}</span>)}
      </div>
      <p className="border-t border-line/80 px-4 py-2.5 text-[9px] text-slate-600 sm:px-5">Route lines show the network topology; node timing follows the engine’s round snapshots.</p>
    </div>

    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,.75fr)]">
      <section className="panel-card p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {playing
              ? <button className="button-primary" onClick={() => setPlaying(false)} aria-label="Pause cascade"><Pause size={14} /> Pause</button>
              : <button className="button-primary" onClick={play} disabled={!hasCascade || snapshots.length === 0} aria-label="Play cascade"><Play size={14} fill="currentColor" /> Play</button>}
            <button className="button-secondary" onClick={() => seek(-1)} aria-label="Replay cascade from start"><RotateCcw size={13} /> Replay</button>
          </div>
          <span className="text-[10px] text-slate-600">{snapshots.length} engine round{snapshots.length === 1 ? '' : 's'}</span>
        </div>
        {!hasCascade && <p className="mt-4 rounded-lg border border-line bg-[#0d1117] px-3 py-2.5 text-[11px] text-slate-400" role="status">No cascade propagated beyond the initially failed facilities.</p>}
        {snapshots.length === 0 && <p className="mt-4 rounded-lg border border-amber-300/15 bg-amber-300/[.04] px-3 py-2.5 text-[11px] text-amber-200/80" role="status">The simulation response contains no round snapshots, so round-by-round playback is unavailable.</p>}
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1" aria-label="Cascade timeline">
          <button onClick={() => seek(-1)} aria-pressed={currentStep === -1} className={`cascade-timeline-step ${currentStep === -1 ? 'cascade-timeline-active' : ''}`}><span>Start</span><b>Initial</b><small>{run.result.failed_nodes.length} failed</small></button>
          {snapshots.map((snapshot, index) => <button key={`${snapshot.round}-${index}`} onClick={() => seek(index)} aria-pressed={currentStep === index} className={`cascade-timeline-step ${currentStep === index ? 'cascade-timeline-active' : ''}`}><span>Round {snapshot.round}</span><b>{snapshot.newly_impacted.length ? `${snapshot.newly_impacted.length} impacted` : 'No new impacts'}</b><small>{snapshot.overloaded_nodes.length} overloaded</small></button>)}
        </div>
      </section>

      <section className="panel-card p-4 sm:p-5" aria-live="polite">
        <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-medium uppercase tracking-[.12em] text-slate-600">Current step</p><h3 className="mt-1 text-sm font-semibold text-slate-200">{currentStep < 0 ? 'Initial disruption' : `Propagation round ${activeSnapshot?.round ?? ''}`}</h3></div><span className="rounded border border-line bg-[#0d1117] px-2 py-1 text-[10px] text-slate-500">{currentAffected.length} node{currentAffected.length === 1 ? '' : 's'}</span></div>
        <p className="mt-3 text-[11px] font-medium text-slate-400">{currentStep < 0 ? 'Initially failed facilities' : 'Nodes affected during this round'}</p>
        {currentAffected.length ? <div className="mt-2 flex flex-wrap gap-1.5">{currentAffected.map((id) => <span key={id} className={`rounded-md border px-2 py-1 font-mono text-[10px] ${currentStep < 0 ? 'border-rose-300/20 bg-rose-300/[.06] text-rose-200' : 'border-amber-300/20 bg-amber-300/[.05] text-amber-100'}`}>{id}</span>)}</div> : <p className="mt-2 text-[11px] text-slate-600">No new facilities were impacted in this round.</p>}
        {activeSnapshot && <div className="mt-4 grid grid-cols-2 gap-2 border-t border-line pt-3 text-[10px]"><div><span className="text-slate-600">Round</span><b className="ml-2 font-medium text-slate-300">{activeSnapshot.round}</b></div><div><span className="text-slate-600">Overloaded</span><b className="ml-2 font-medium text-slate-300">{activeSnapshot.overloaded_nodes.length}</b></div></div>}
      </section>
    </div>
  </section>
}
