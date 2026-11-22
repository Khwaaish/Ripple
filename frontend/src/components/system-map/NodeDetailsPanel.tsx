import { ArrowDownLeft, ArrowUpRight, Boxes, Factory, Store } from 'lucide-react'
import type { NetworkEdge, NetworkNode } from '../../api/types'

type NodeDetailsPanelProps = {
  facility: NetworkNode | null
  edges: NetworkEdge[]
  onClear: () => void
}

const iconByType = { supplier: Factory, warehouse: Boxes, store: Store }
const nameByType = { supplier: 'Supplier', warehouse: 'Warehouse', store: 'Retail store' }
const properties: { key: keyof NetworkNode; label: string; unit?: string }[] = [
  { key: 'id', label: 'Facility ID' },
  { key: 'type', label: 'Facility type' },
  { key: 'capacity', label: 'Capacity', unit: 'units' },
  { key: 'load', label: 'Load', unit: 'units' },
  { key: 'buffer_hours', label: 'Buffer', unit: 'hours' },
  { key: 'critical', label: 'Critical facility' },
  { key: 'criticality_weight', label: 'Criticality weight' },
  { key: 'recovery_hours', label: 'Recovery estimate', unit: 'hours' },
  { key: 'unit_cost', label: 'Unit cost' },
]

function prettyValue(key: keyof NetworkNode, value: NetworkNode[keyof NetworkNode]) {
  if (value === null || value === undefined) return 'Not specified'
  if (key === 'critical') return value ? 'Yes' : 'No'
  if (key === 'type') return nameByType[value as NetworkNode['type']]
  return String(value)
}

function ConnectionRow({ edge, direction }: { edge: NetworkEdge; direction: 'inbound' | 'outbound' }) {
  const inbound = direction === 'inbound'
  const Icon = inbound ? ArrowDownLeft : ArrowUpRight
  const endpoint = inbound ? edge.src : edge.dst
  return <div className="rounded-lg border border-line bg-[#0d1117] px-3 py-2.5">
    <div className="flex items-center gap-2"><Icon size={13} className={edge.is_alt ? 'text-amber-300' : 'text-slate-500'} /><span className="text-xs font-medium text-slate-200">{inbound ? `${endpoint} → this facility` : `this facility → ${endpoint}`}</span>{edge.is_alt && <span className="ml-auto rounded border border-amber-300/10 bg-amber-300/[.06] px-1.5 py-0.5 text-[8px] font-semibold text-amber-300">ALT</span>}</div>
    <p className="ml-5 mt-1.5 text-[10px] text-slate-500">{Math.round(edge.share * 100)}% share <span className="mx-1 text-slate-700">·</span> {edge.capacity} capacity <span className="mx-1 text-slate-700">·</span> {edge.delay_h}h delay</p>
    <p className="ml-5 mt-1 text-[10px] text-slate-600">Reliability {Math.round(edge.reliability * 100)}%</p>
  </div>
}

export function NodeDetailsPanel({ facility, edges, onClear }: NodeDetailsPanelProps) {
  if (!facility) return <aside className="panel-card flex min-h-[220px] flex-col items-center justify-center p-5 text-center xl:sticky xl:top-[96px] xl:h-[calc(100vh-170px)]"><div className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-[#0d1117] text-slate-500"><Boxes size={17} /></div><p className="mt-3 text-sm font-medium text-slate-300">Select a facility</p><p className="mt-1 max-w-[220px] text-[11px] leading-relaxed text-slate-600">Choose any node on the map to inspect its properties and connected routes.</p></aside>

  const Icon = iconByType[facility.type]
  const inbound = edges.filter((edge) => edge.dst === facility.id)
  const outbound = edges.filter((edge) => edge.src === facility.id)
  return <aside className="panel-card overflow-hidden xl:sticky xl:top-[96px] xl:max-h-[calc(100vh-170px)] xl:overflow-y-auto">
    <div className="border-b border-line p-4">
      <div className="flex items-start gap-3"><span className={`facility-detail-icon detail-${facility.type}`}><Icon size={16} /></span><div className="min-w-0 flex-1"><p className="text-[10px] uppercase tracking-[.13em] text-slate-600">Selected facility</p><h3 className="mt-1 truncate text-base font-semibold text-slate-100">{facility.id}</h3><p className="mt-0.5 text-[11px] text-slate-500">{nameByType[facility.type]}</p></div>{facility.critical && <span className="critical-tag mt-1">CRITICAL</span>}</div>
    </div>
    <div className="p-4">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-[.12em] text-slate-600">Facility properties</p>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-3">{properties.map(({ key, label, unit }) => <div key={key} className="min-w-0"><dt className="text-[10px] text-slate-600">{label}</dt><dd className="mt-1 truncate text-xs font-medium text-slate-300">{prettyValue(key, facility[key])}{unit && facility[key] !== null ? <span className="ml-1 text-[9px] font-normal text-slate-600">{unit}</span> : null}</dd></div>)}</dl>
    </div>
    <div className="border-t border-line p-4">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-[.12em] text-slate-600">Connections <span className="ml-1 font-normal normal-case tracking-normal">({inbound.length + outbound.length})</span></p>
      <div className="space-y-2">
        {inbound.map((edge) => <ConnectionRow key={`in-${edge.src}-${edge.dst}`} edge={edge} direction="inbound" />)}
        {outbound.map((edge) => <ConnectionRow key={`out-${edge.src}-${edge.dst}`} edge={edge} direction="outbound" />)}
        {inbound.length + outbound.length === 0 && <p className="rounded-lg border border-dashed border-line px-3 py-4 text-center text-[11px] text-slate-600">No connected routes.</p>}
      </div>
    </div>
    <button className="m-4 mt-0 text-[10px] text-slate-600 transition hover:text-slate-300" onClick={onClear}>Clear selection</button>
  </aside>
}
