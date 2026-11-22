import { ArrowRight, Bot, Check, ChevronRight, CircleHelp, FileText, Lightbulb, Sparkles, Waves } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const insights = [
  { label: 'Most exposed tier', value: 'Warehouses', detail: '2 of 3 facilities are upstream of high-volume retail locations.' },
  { label: 'Highest leverage', value: 'WH-02 alternate route', detail: 'Modeled rerouting lowers weighted impact in the regional port scenario.' },
  { label: 'Critical watch', value: 'SUP-01 · Elevated', detail: 'A supplier delay is being monitored; downstream buffers remain available.' },
]

export function AIAnalystPage() {
  return <div className="space-y-6 pb-10">
    <SectionHeading title="AI analyst" description="Plain-language context grounded in Ripple’s deterministic outputs." action={<button className="button-secondary"><CircleHelp size={14} /> About insights</button>} />
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,.75fr)]">
      <section className="panel-card overflow-hidden">
        <div className="flex items-center gap-3 border-b border-line bg-gradient-to-r from-mint/[.06] to-transparent p-5 sm:px-6"><div className="brand-mark h-9 w-9 rounded-xl"><Bot size={18} /></div><div className="flex-1"><p className="text-sm font-semibold text-slate-200">Network briefing</p><p className="mt-0.5 text-[10px] text-slate-600">Generated from mock dashboard data · Today, 9:42 AM</p></div><span className="flex items-center gap-1.5 rounded-full border border-mint/10 bg-mint/[.06] px-2.5 py-1 text-[10px] text-mint"><span className="status-dot status-dot-green" /> Ready</span></div>
        <div className="p-5 sm:p-7"><div className="flex items-start gap-3"><Sparkles size={16} className="mt-1 shrink-0 text-mint" /><p className="text-sm leading-7 text-slate-300">Overall network health is <span className="font-semibold text-slate-100">stable at 94.2</span>. A supplier delay at SUP-01 is the primary active signal, though current downstream buffers provide a useful response window. The regional port scenario shows the strongest modeled benefit from rerouting through available alternate capacity.</p></div>
          <div className="mt-7 grid gap-3">{insights.map((item, i) => <div key={item.label} className="flex gap-3 rounded-xl border border-line bg-[#0d1117] p-4"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-panel text-[10px] font-semibold text-slate-500">0{i + 1}</span><div className="flex-1"><p className="text-[10px] uppercase tracking-wider text-slate-600">{item.label}</p><p className="mt-1 text-xs font-medium text-slate-200">{item.value}</p><p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.detail}</p></div><Check size={14} className="mt-1 shrink-0 text-mint/70" /></div>)}</div>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5"><div className="flex items-center gap-2 text-[10px] text-slate-600"><FileText size={13} /> 3 signals referenced <span className="mx-1">·</span> Engine-backed summary</div><button className="text-xs text-slate-400 hover:text-slate-200">View source run <ArrowRight size={13} className="ml-1 inline" /></button></div>
        </div>
      </section>
      <aside className="space-y-5">
        <div className="panel-card p-5"><div className="flex items-center gap-2"><Waves size={15} className="text-mint" /><h3 className="text-sm font-semibold text-slate-200">Ask about your network</h3></div><p className="mt-2 text-xs leading-relaxed text-slate-500">The analyst workspace will support grounded questions about scenarios and modeled outcomes.</p><div className="mt-4 flex items-center gap-2 rounded-lg border border-line bg-[#0d1117] px-3 py-2.5 text-[11px] text-slate-600">Ask a question <ChevronRight size={13} className="ml-auto" /></div><button className="mt-3 w-full rounded-lg bg-mint/10 px-3 py-2.5 text-xs font-medium text-mint/80">Conversation coming soon</button></div>
        <div className="rounded-xl border border-sky-400/10 bg-gradient-to-br from-sky-400/[.06] to-transparent p-5"><Lightbulb size={17} className="text-sky-300" /><p className="mt-3 text-sm font-medium text-slate-200">Insight guardrails</p><p className="mt-2 text-xs leading-relaxed text-slate-500">Summaries should explain the engine’s calculated outcomes and keep assumptions visible.</p><button className="mt-4 text-xs font-medium text-sky-300/80">Read methodology <ArrowRight size={13} className="ml-1 inline" /></button></div>
      </aside>
    </div>
  </div>
}
