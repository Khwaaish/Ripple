import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Boxes, Factory, Store } from 'lucide-react'
import type { FacilityFlowNode } from './types'

const icons = { supplier: Factory, warehouse: Boxes, store: Store }
const labels = { supplier: 'Supplier', warehouse: 'Warehouse', store: 'Retail store' }

export function FacilityNodeView({ data, selected }: NodeProps<FacilityFlowNode>) {
  const facility = data.facility
  const Icon = icons[facility.type]
  const utilization = facility.capacity > 0 ? Math.min(100, (facility.load / facility.capacity) * 100) : 0
  return (
    <div className={`facility-node facility-${facility.type} ${selected ? 'facility-node-selected' : ''}`} aria-label={`${labels[facility.type]} ${facility.id}`}>
      <Handle type="target" position={Position.Left} className="facility-handle" />
      <div className="flex items-center gap-2">
        <span className="facility-icon"><Icon size={13} strokeWidth={1.8} /></span>
        <span className="min-w-0 flex-1 truncate text-[12px] font-semibold text-slate-100">{facility.id}</span>
        {facility.critical && <span className="critical-tag">CRITICAL</span>}
      </div>
      <p className="mt-1 text-[9px] font-medium uppercase tracking-[.12em] text-slate-500">{labels[facility.type]}</p>
      <div className="mt-2 flex items-center justify-between text-[9px] text-slate-400"><span>Load <b className="font-semibold text-slate-200">{facility.load}</b></span><span>Capacity <b className="font-semibold text-slate-300">{facility.capacity}</b></span></div>
      <div className="mt-1 h-[3px] overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-current opacity-80" style={{ width: `${utilization}%` }} /></div>
      <div className="mt-1.5 flex items-center justify-between text-[9px] text-slate-600"><span>{facility.buffer_hours}h buffer</span><span>{facility.recovery_hours}h recovery</span></div>
      <Handle type="source" position={Position.Right} className="facility-handle" />
    </div>
  )
}
