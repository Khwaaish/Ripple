import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  ReactFlow,
  type EdgeTypes,
  type NodeTypes,
} from '@xyflow/react'
import type { NetworkEdge, NetworkNode, SupplyNetwork } from '../../api/types'
import { FacilityNodeView } from './FacilityNodeView'
import { SupplyEdgeView } from './SupplyEdgeView'
import type { FacilityFlowNode, SupplyFlowEdge } from './types'

const NODE_WIDTH = 194
const NODE_HEIGHT = 90
const MAP_HEIGHT = 630
const nodeTypes: NodeTypes = { facility: FacilityNodeView }
const edgeTypes: EdgeTypes = { supply: SupplyEdgeView }

export function nodePositions(nodes: NetworkNode[]) {
  const groups: Record<NetworkNode['type'], NetworkNode[]> = { supplier: [], warehouse: [], store: [] }
  for (const node of [...nodes].sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }))) groups[node.type].push(node)
  const positions = new Map<string, { x: number; y: number }>()
  const columns: { type: NetworkNode['type']; x: number; yStart: number; yEnd: number }[] = [
    { type: 'supplier', x: 24, yStart: 86, yEnd: 470 },
    { type: 'warehouse', x: 314, yStart: 154, yEnd: 402 },
    { type: 'store', x: 604, yStart: 8, yEnd: 508 },
  ]
  for (const column of columns) {
    const rows = groups[column.type]
    rows.forEach((node, index) => {
      const y = rows.length <= 1
        ? (MAP_HEIGHT - NODE_HEIGHT) / 2
        : column.yStart + ((column.yEnd - column.yStart) * index) / (rows.length - 1)
      positions.set(node.id, { x: column.x, y })
    })
  }
  return positions
}

export function spaceEdgeLabels(edges: NetworkEdge[], positions: Map<string, { x: number; y: number }>) {
  const grouped = new Map<string, { edge: NetworkEdge; baseY: number; order: number }[]>()
  edges.forEach((edge, order) => {
    const source = positions.get(edge.src)!
    const target = positions.get(edge.dst)!
    const key = `${source.x}:${target.x}`
    const entries = grouped.get(key) ?? []
    entries.push({ edge, baseY: (source.y + target.y) / 2 + NODE_HEIGHT / 2, order })
    grouped.set(key, entries)
  })
  const offset = new Map<string, number>()
  for (const entries of grouped.values()) {
    entries.sort((a, b) => a.baseY - b.baseY || a.order - b.order)
    let previous = -Infinity
    const adjusted = entries.map(({ edge, baseY }) => {
      const y = Math.max(baseY, previous + 34)
      previous = y
      return { edge, baseY, y }
    })
    const lastY = adjusted[adjusted.length - 1]?.y ?? 0
    const overflow = Math.max(0, lastY - (MAP_HEIGHT - 24))
    adjusted.forEach(({ edge, baseY, y }) => offset.set(`${edge.src}->${edge.dst}`, y - overflow - baseY))
  }
  return offset
}

export function SystemMapGraph({ network, selectedNodeId, onSelectNode }: {
  network: SupplyNetwork
  selectedNodeId: string | null
  onSelectNode: (nodeId: string | null) => void
}) {
  const positions = useMemo(() => nodePositions(network.nodes), [network.nodes])
  const labelOffsets = useMemo(() => spaceEdgeLabels(network.edges, positions), [network.edges, positions])
  const nodes = useMemo<FacilityFlowNode[]>(() => network.nodes.map((facility) => ({
    id: facility.id,
    type: 'facility',
    position: positions.get(facility.id)!,
    data: { facility, selected: selectedNodeId === facility.id },
    selected: selectedNodeId === facility.id,
    draggable: false,
    selectable: true,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    style: { width: NODE_WIDTH, height: NODE_HEIGHT },
  })), [network.nodes, positions, selectedNodeId])
  const edges = useMemo<SupplyFlowEdge[]>(() => network.edges.map((supply, index) => ({
    id: `${supply.src}-${supply.dst}`,
    source: supply.src,
    target: supply.dst,
    type: 'supply',
    data: { supply, labelOffsetY: labelOffsets.get(`${supply.src}->${supply.dst}`) ?? 0 },
    markerEnd: { type: MarkerType.ArrowClosed, color: supply.is_alt ? '#d9a86f' : '#65768a', width: 13, height: 13 },
    zIndex: supply.is_alt ? 0 : 1,
    ariaLabel: `Supply route ${supply.src} to ${supply.dst}`,
    selectable: false,
    focusable: false,
    style: { stroke: supply.is_alt ? '#d9a86f' : '#65768a', strokeDasharray: supply.is_alt ? '5 5' : undefined },
  })), [network.edges, labelOffsets])

  return <div className="system-flow-canvas" role="application" aria-label="Interactive 12-facility supply network map">
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
      elementsSelectable
      panOnDrag
      zoomOnScroll
      zoomOnPinch
      onNodeClick={(_, node) => onSelectNode(node.id)}
      onPaneClick={() => onSelectNode(null)}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#27313d" />
      <Controls showInteractive={false} position="bottom-left" />
    </ReactFlow>
  </div>
}
