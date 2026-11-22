import { ArrowRight, ArrowUpRight, Boxes, Check, Clock3, MapPin, MoreHorizontal, Radio, Signal, TriangleAlert, Zap } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { SectionHeading } from '../components/SectionHeading'
import { events, exposedTiers, metrics, watchlist } from '../data/mockData'

function ResilienceChart() {
  return (
    <div className="mt-5">
      <div className="flex items-center justify-between text-[10px] text-slate-600"><span>100</span><span>75</span><span>50</span><span>25</span></div>
      <div className="relative mt-2 h-[142px] overflow-hidden rounded-lg bg-[#0d1117]">
        <div className="chart-grid absolute inset-0" />
        <svg viewBox="0 0 640 150" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
          <defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#58d6b0" stopOpacity=".17" /><stop offset="100%" stopColor="#58d6b0" stopOpacity="0" /></linearGradient></defs>
          <path d="M0 106 C28 98 38 111 64 96 S105 89 128 94 S164 70 192 82 S228 92 256 70 S295 81 320 63 S352 67 384 50 S417 72 448 51 S482 62 512 38 S550 51 576 32 S610 40 640 22 L640 150 L0 150Z" fill="url(#chartFill)" />
          <path d="M0 106 C28 98 38 111 64 96 S105 89 128 94 S164 70 192 82 S228 92 256 70 S295 81 320 63 S352 67 384 50 S417 72 448 51 S482 62 512 38 S550 51 576 32 S610 40 640 22" fill="none" stroke="#58d6b0" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
          <circle cx="576" cy="32" r="4" fill="#58d6b0" stroke="#0d1117" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="absolute right-3 top-3 rounded-md border border-mint/15 bg-mint/10 px-2 py-1 text-[10px] font-medium text-mint">94.2 health</div>
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-slate-600"><span>Oct 15</span><span>Oct 18</span><span>Oct 21</span><span>Oct 24</span><span>Oct 28</span></div>
    </div>
  )
}

export function OverviewPage({ onNavigate }: { onNavigate: (section: 'Scenario Creator' | 'Ripple Simulation') => void }) {
  return (
    <div className="space-y-7 pb-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[.15em] text-mint/80"><span className="status-dot status-dot-green" /> Operations overview</div>
          <h2 className="text-[26px] font-semibold tracking-tight text-slate-50">Good morning, Alex</h2>
          <p className="mt-1.5 text-sm text-slate-500">Here’s the latest resilience picture for your supply network.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => onNavigate('Ripple Simulation')} className="button-secondary"><Clock3 size={15} /> Recent runs</button>
          <button onClick={() => onNavigate('Scenario Creator')} className="button-primary"><Zap size={15} /> New scenario</button>
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(330px,1fr)]">
        <article className="panel-card p-5 sm:p-6">
          <SectionHeading title="Network resilience" description="Composite network health · last 14 days" action={<button className="icon-button" aria-label="More network resilience options"><MoreHorizontal size={18} /></button>} />
          <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
            <div><p className="text-[38px] font-semibold leading-none tracking-tight text-slate-50">94.2<span className="ml-1 text-lg font-medium text-slate-500">/100</span></p><p className="mt-2 flex items-center gap-1 text-xs text-mint"><ArrowUpRight size={14} /> 2.4% <span className="text-slate-600">from previous period</span></p></div>
            <div className="mb-1 flex gap-4 text-[11px] text-slate-500"><span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-mint" /> Network health</span><span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-slate-600" /> Threshold</span></div>
          </div>
          <ResilienceChart />
        </article>

        <article className="panel-card p-5 sm:p-6">
          <SectionHeading title="Network by tier" description="Facility health at a glance" action={<button className="text-xs font-medium text-slate-400 transition hover:text-slate-200">View map <ArrowRight size={13} className="ml-1 inline" /></button>} />
          <div className="mt-6 space-y-6">
            {exposedTiers.map((tier) => <div key={tier.name}>
              <div className="mb-2 flex items-center justify-between"><div><p className="text-sm font-medium text-slate-200">{tier.name}</p><p className="mt-0.5 text-[11px] text-slate-500">{tier.count}</p></div><span className="text-sm font-semibold text-slate-200">{tier.health}%</span></div>
              <div className="h-1.5 rounded-full bg-slate-800"><div className={`h-1.5 rounded-full ${tier.color}`} style={{ width: `${tier.health}%` }} /></div>
            </div>)}
          </div>
          <div className="mt-7 flex items-center justify-between border-t border-line pt-4 text-xs"><span className="flex items-center gap-2 text-slate-500"><Boxes size={14} /> 12 facilities tracked</span><span className="flex items-center gap-1.5 text-mint"><Signal size={13} /> Stable</span></div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <article className="panel-card overflow-hidden">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3"><SectionHeading title="Recent network events" description="Signals and simulation activity" action={<button className="text-xs text-slate-400 hover:text-slate-200">View all <ArrowRight size={13} className="ml-1 inline" /></button>} /></div>
          <div className="divide-y divide-line/80">
            {events.map((event) => <div key={event.title} className="flex items-center gap-3 px-5 py-4 transition hover:bg-white/[.015] sm:px-6">
              <div className={`event-icon event-${event.tone}`}>{event.tone === 'amber' ? <TriangleAlert size={15} /> : event.tone === 'mint' ? <Check size={15} /> : <Radio size={15} />}</div>
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-200">{event.title}</p><p className="mt-1 truncate text-[11px] text-slate-500">{event.location}</p></div>
              <div className="hidden shrink-0 text-right sm:block"><p className={`text-[10px] font-medium ${event.tone === 'mint' ? 'text-mint' : event.tone === 'amber' ? 'text-amber-300' : 'text-sky-300'}`}>{event.status}</p><p className="mt-1 text-[10px] text-slate-600">{event.time}</p></div>
            </div>)}
          </div>
        </article>

        <article className="panel-card overflow-hidden">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3"><SectionHeading title="Priority watchlist" description="Nodes with the highest exposure" action={<button className="icon-button" aria-label="Open watchlist"><ArrowUpRight size={16} /></button>} /></div>
          <div className="divide-y divide-line/80">
            {watchlist.map((node, index) => <div key={node.id} className="flex items-center gap-3 px-5 py-3.5 sm:px-6">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-[#0d1117] text-[10px] font-semibold text-slate-400">0{index + 1}</div>
              <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="truncate text-sm font-medium text-slate-200">{node.name}</p><span className="hidden text-[10px] text-slate-600 md:inline">{node.id}</span></div><p className="mt-1 text-[11px] text-slate-500">{node.type}</p></div>
              <div className="text-right"><p className={`text-xs font-medium ${node.tone === 'amber' ? 'text-amber-300' : node.tone === 'mint' ? 'text-mint' : 'text-sky-300'}`}>{node.risk}</p><p className="mt-1 text-[10px] text-slate-600">Risk {node.score}</p></div>
              <MapPin size={14} className="ml-1 text-slate-600" />
            </div>)}
          </div>
          <div className="mx-5 mb-5 mt-2 flex items-center justify-between rounded-lg border border-amber-400/10 bg-amber-300/[.035] px-3 py-2.5 sm:mx-6"><span className="flex items-center gap-2 text-[11px] text-slate-400"><TriangleAlert size={14} className="text-amber-300" /> 1 facility requires review</span><span className="text-[10px] text-amber-200/80">Open queue <ArrowRight size={12} className="ml-1 inline" /></span></div>
        </article>
      </section>
    </div>
  )
}
