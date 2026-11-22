import { Activity, Boxes, ShieldAlert, Timer, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const iconMap: Record<string, LucideIcon> = { Activity, Boxes, ShieldAlert, Timer }

type MetricCardProps = {
  label: string
  value: string
  change: string
  detail: string
  icon: string
  tone: string
}

export function MetricCard({ label, value, change, detail, icon, tone }: MetricCardProps) {
  const Icon = iconMap[icon] ?? Activity
  const positive = change.startsWith('+') || change.startsWith('−') || change === 'All online'
  return (
    <article className="panel-card group p-5 transition duration-200 hover:border-slate-600/80 hover:bg-panel/90">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-400">{label}</p>
        <span className={`icon-tile icon-${tone}`}><Icon size={17} strokeWidth={1.8} /></span>
      </div>
      <div className="mt-5 flex items-end justify-between gap-3">
        <p className="text-[28px] font-semibold tracking-tight text-slate-50">{value}</p>
        <div className={`mb-1 inline-flex items-center gap-1 text-xs font-medium ${positive ? 'text-mint' : 'text-amber-300'}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{change}
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </article>
  )
}
