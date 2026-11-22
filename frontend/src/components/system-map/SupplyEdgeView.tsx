import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'
import type { SupplyFlowEdge } from './types'

export function SupplyEdgeView({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, data, selected }: EdgeProps<SupplyFlowEdge>) {
  if (!data) return null
  const { supply, labelOffsetY } = data
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.18 })
  const stroke = supply.is_alt ? '#d9a86f' : '#65768a'
  const title = `${Math.round(supply.share * 100)}% share · capacity ${supply.capacity} · ${supply.delay_h}h delay · reliability ${Math.round(supply.reliability * 100)}%${supply.is_alt ? ' · alternate route' : ''}`
  return <>
    <BaseEdge id={id} path={path} markerEnd={markerEnd} style={{ stroke, strokeWidth: selected ? 2.4 : 1.5, strokeDasharray: supply.is_alt ? '5 5' : undefined }} />
    <EdgeLabelRenderer>
      <div className={`supply-edge-label ${supply.is_alt ? 'supply-edge-alt' : ''}`} title={title} style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY + labelOffsetY}px)` }}>
        <span className="font-semibold">{Math.round(supply.share * 100)}%</span><span className="edge-label-divider" />
        <span>{supply.capacity} cap</span><span className="edge-label-divider" /><span>{supply.delay_h}h</span>
        {supply.is_alt && <span className="edge-alt-tag">ALT</span>}
      </div>
    </EdgeLabelRenderer>
  </>
}
