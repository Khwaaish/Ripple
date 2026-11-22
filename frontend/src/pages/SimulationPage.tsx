import { ArrowDownRight, ArrowRight, CalendarDays, Clock3, Play, Plus, Radio, RotateCcw } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const runs = [
  { name: 'Regional port disruption', date: 'Oct 28, 2026 · 09:42 AM', status: 'Completed', impact: '31.4%', strategy: 'Reroute', duration: '0.8s' },
  { name: 'Supplier capacity reduction', date: 'Oct 27, 2026 · 03:16 PM', status: 'Completed', impact: '18.7%', strategy: 'Baseline', duration: '0.6s' },
  { name: 'Warehouse WH-02 outage', date: 'Oct 26, 2026 · 11:08 AM', status: 'Completed', impact: '24.1%', strategy: 'Prioritize', duration: '0.7s' },
]

export function SimulationPage() {
  return <div className="space-y-6 pb-10">
    <SectionHeading title="Ripple simulation" description="Run deterministic cascade scenarios against your network." action={<button className="button-primary"><Play size={14} fill="currentColor" /> Run simulation</button>} />
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="panel-card p-5"><p className="text-xs text-slate-500">Simulations this week</p><p className="mt-3 text-2xl font-semibold text-slate-100">18</p><p className="mt-2 text-[11px] text-mint">+4 vs. last week</p></div>
      <div className="panel-card p-5"><p className="text-xs text-slate-500">Median runtime</p><p className="mt-3 text-2xl font-semibold text-slate-100">0.7<span className="ml-1 text-sm font-medium text-slate-500">sec</span></p><p className="mt-2 text-[11px] text-slate-600">Deterministic engine</p></div>
      <div className="panel-card p-5"><p className="text-xs text-slate-500">Lowest modeled impact</p><p className="mt-3 text-2xl font-semibold text-slate-100">12.3<span className="ml-1 text-sm font-medium text-slate-500">%</span></p><p className="mt-2 flex items-center gap-1 text-[11px] text-mint"><ArrowDownRight size={13} /> With intervention</p></div>
    </div>
    <section className="panel-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-5 sm:px-6"><div><h3 className="text-sm font-semibold text-slate-200">Recent simulation runs</h3><p className="mt-1 text-xs text-slate-500">Mock activity for dashboard layout</p></div><div className="flex gap-2"><button className="button-secondary"><CalendarDays size={14} /> Last 7 days</button><button className="toolbar-button" aria-label="Refresh simulations"><RotateCcw size={15} /></button></div></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left"><thead><tr className="border-b border-line bg-white/[.015] text-[10px] uppercase tracking-wider text-slate-600"><th className="px-6 py-3 font-medium">Scenario</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Impact score</th><th className="px-4 py-3 font-medium">Best strategy</th><th className="px-4 py-3 font-medium">Runtime</th><th className="px-6 py-3" /></tr></thead><tbody className="divide-y divide-line/70">{runs.map((run) => <tr key={run.name} className="text-xs transition hover:bg-white/[.015]"><td className="px-6 py-4"><p className="font-medium text-slate-200">{run.name}</p><p className="mt-1 text-[10px] text-slate-600">{run.date}</p></td><td className="px-4 py-4"><span className="inline-flex items-center gap-1.5 text-mint"><span className="h-1.5 w-1.5 rounded-full bg-mint" />{run.status}</span></td><td className="px-4 py-4 font-medium text-slate-300">{run.impact}</td><td className="px-4 py-4"><span className="rounded-md border border-line bg-panel px-2 py-1 text-[10px] text-slate-400">{run.strategy}</span></td><td className="px-4 py-4 text-slate-500">{run.duration}</td><td className="px-6 py-4 text-right"><button className="text-slate-600 hover:text-slate-300" aria-label={`Open ${run.name}`}><ArrowRight size={15} /></button></td></tr>)}</tbody></table></div>
      <div className="flex items-center justify-between border-t border-line px-6 py-3 text-[10px] text-slate-600"><span>Showing 3 of 18 runs</span><button className="text-slate-400 hover:text-slate-200">View all runs</button></div>
    </section>
    <div className="flex items-center gap-3 rounded-xl border border-line bg-panel/65 p-4"><div className="icon-tile icon-blue"><Radio size={17} /></div><div className="flex-1"><p className="text-xs font-medium text-slate-300">No simulation is currently running</p><p className="mt-1 text-[11px] text-slate-600">Create or select a scenario to explore its modeled cascade.</p></div><button className="button-secondary max-sm:hidden"><Plus size={14} /> New scenario</button><Clock3 size={15} className="text-slate-600 sm:hidden" /></div>
  </div>
}
