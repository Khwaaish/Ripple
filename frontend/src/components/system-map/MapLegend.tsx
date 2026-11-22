import { Boxes, Factory, Store } from 'lucide-react'

export function MapLegend() {
  return <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] text-slate-500">
    <span className="flex items-center gap-1.5"><i className="legend-node legend-supplier"><Factory size={9} /></i>Supplier</span>
    <span className="flex items-center gap-1.5"><i className="legend-node legend-warehouse"><Boxes size={9} /></i>Warehouse</span>
    <span className="flex items-center gap-1.5"><i className="legend-node legend-store"><Store size={9} /></i>Retail store</span>
    <span className="ml-1 flex items-center gap-1.5"><i className="legend-line" />Primary supply</span>
    <span className="flex items-center gap-1.5"><i className="legend-line legend-line-alt" />Alternate route</span>
  </div>
}
