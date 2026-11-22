import { ArrowRight, Check, CircleHelp, Clock3, Coins, Route, ShieldCheck, Target, Truck } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'
import { strategies } from '../data/mockData'

const icons = [Route, Truck, Target]

export function InterventionCenterPage() {
  return <div className="space-y-6 pb-10">
    <SectionHeading title="Intervention center" description="Compare modeled response strategies and their trade-offs." action={<button className="button-secondary"><CircleHelp size={14} /> How recommendations work</button>} />
    <div className="grid gap-4 lg:grid-cols-3">{strategies.map((strategy, index) => {
      const Icon = icons[index]
      return <article key={strategy.title} className="panel-card relative overflow-hidden p-5 transition hover:border-slate-600/80 sm:p-6"><div className={`absolute right-0 top-0 h-28 w-28 rounded-full blur-3xl ${strategy.color === 'mint' ? 'bg-mint/[.06]' : strategy.color === 'blue' ? 'bg-sky-400/[.06]' : 'bg-violet-400/[.06]'}`} /><div className="relative"><div className="flex items-start justify-between"><span className={`icon-tile icon-${strategy.color}`}><Icon size={18} /></span><span className="rounded-full border border-line bg-[#0d1117] px-2.5 py-1 text-[10px] text-slate-500">{strategy.tag}</span></div><h3 className="mt-5 text-base font-semibold text-slate-100">{strategy.title}</h3><p className="mt-2 min-h-[58px] text-xs leading-relaxed text-slate-500">{strategy.text}</p><div className="mt-5 border-t border-line pt-4"><p className="text-[10px] uppercase tracking-wider text-slate-600">Modeled impact change</p><p className={`mt-1 text-2xl font-semibold ${strategy.color === 'mint' ? 'text-mint' : strategy.color === 'blue' ? 'text-sky-300' : 'text-violet-300'}`}>{strategy.impact}</p></div><button className="mt-5 flex w-full items-center justify-between rounded-lg border border-line px-3 py-2.5 text-xs text-slate-400 transition hover:bg-white/[.03] hover:text-slate-200">View strategy details <ArrowRight size={14} /></button></div></article>
    })}</div>
    <section className="panel-card p-5 sm:p-6"><SectionHeading title="Recommendation priorities" description="How Ripple ranks candidate interventions" /><div className="grid gap-3 md:grid-cols-3">{[{ icon: ShieldCheck, title: 'Weighted impact', body: 'Reduce shortage pressure across all affected facilities.' }, { icon: Clock3, title: 'Recovery time', body: 'Prefer strategies that restore normal flow sooner.' }, { icon: Coins, title: 'Operational cost', body: 'Use cost as a tie-breaker after resilience outcomes.' }].map(({ icon: Icon, title, body }, i) => <div key={title} className="flex gap-3 rounded-xl border border-line bg-[#0d1117] p-4"><span className="text-[10px] font-semibold text-slate-700">0{i + 1}</span><div className="flex-1"><div className="flex items-center gap-2 text-xs font-medium text-slate-300"><Icon size={14} className="text-slate-500" />{title}</div><p className="mt-2 text-[11px] leading-relaxed text-slate-600">{body}</p></div><Check size={14} className="mt-0.5 text-mint/70" /></div>)}</div></section>
  </div>
}
