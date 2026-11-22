import { ArrowRight, Check, CircleHelp, GitBranch, Plus, SlidersHorizontal, Sparkles, Waypoints } from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const steps = [
  { number: '01', title: 'Choose a disruption', text: 'Select a facility and disruption profile.', icon: GitBranch, active: true },
  { number: '02', title: 'Set the scope', text: 'Adjust timing, duration, and severity.', icon: SlidersHorizontal, active: false },
  { number: '03', title: 'Review scenario', text: 'Validate inputs before simulation.', icon: Check, active: false },
]

export function ScenarioCreatorPage() {
  return <div className="space-y-6 pb-10">
    <SectionHeading title="Scenario creator" description="Build a controlled disruption to explore network exposure." action={<button className="button-secondary"><CircleHelp size={14} /> Scenario guide</button>} />
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,.75fr)]">
      <section className="panel-card p-5 sm:p-7">
        <div className="flex items-start justify-between"><div><p className="text-xs font-medium text-mint">NEW SCENARIO</p><h3 className="mt-2 text-lg font-semibold text-slate-100">Start with a disruption</h3><p className="mt-1 text-sm text-slate-500">Choose a node and define the event characteristics.</p></div><span className="icon-tile icon-mint"><Waypoints size={18} /></span></div>
        <div className="mt-7 grid gap-5 sm:grid-cols-2">
          <label className="field-label">Scenario name<input className="dark-input mt-2" placeholder="e.g. Port of Seattle delay" /></label>
          <label className="field-label">Disruption type<select className="dark-input mt-2" defaultValue="supplier"><option value="supplier">Supplier outage</option><option value="warehouse">Warehouse disruption</option><option value="transport">Transport delay</option><option value="store">Store demand shock</option></select></label>
          <label className="field-label sm:col-span-2">Affected facility<select className="dark-input mt-2" defaultValue="SUP-01"><option value="SUP-01">SUP-01 · Northstar Components</option><option value="WH-02">WH-02 · Portland Distribution</option><option value="ST-04">ST-04 · Seattle Central</option></select></label>
        </div>
        <div className="mt-6 rounded-xl border border-line bg-[#0d1117] p-4"><div className="flex items-center justify-between"><div><p className="text-sm font-medium text-slate-200">Disruption duration</p><p className="mt-1 text-xs text-slate-500">Estimated time before normal operations resume</p></div><span className="rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-medium text-slate-300">24 hours</span></div><input type="range" min="1" max="72" defaultValue="24" className="mt-4 w-full accent-emerald-400" /><div className="mt-1 flex justify-between text-[10px] text-slate-600"><span>1h</span><span>72h</span></div></div>
        <div className="mt-7 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5"><p className="text-[11px] text-slate-600">Drafts are local to this prototype.</p><button className="button-primary"><Plus size={15} /> Create scenario <ArrowRight size={14} /></button></div>
      </section>
      <aside className="space-y-5">
        <div className="panel-card p-5"><p className="text-sm font-semibold text-slate-200">Workflow</p><div className="mt-5 space-y-5">{steps.map(({ number, title, text, icon: Icon, active }) => <div key={number} className="flex gap-3"><div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${active ? 'border-mint/25 bg-mint/10 text-mint' : 'border-line bg-[#0d1117] text-slate-500'}`}><Icon size={15} /></div><div><div className="flex items-center gap-2"><span className="text-[10px] text-slate-600">{number}</span><p className={`text-xs font-medium ${active ? 'text-slate-200' : 'text-slate-400'}`}>{title}</p></div><p className="mt-1 text-[11px] text-slate-600">{text}</p></div></div>)}</div></div>
        <div className="rounded-xl border border-mint/10 bg-gradient-to-br from-mint/[.08] to-transparent p-5"><Sparkles size={17} className="text-mint" /><p className="mt-3 text-sm font-medium text-slate-200">Start from a template</p><p className="mt-1 text-xs leading-relaxed text-slate-500">Use a common event pattern as a starting point for your scenario.</p><button className="mt-4 text-xs font-medium text-mint">Browse templates <ArrowRight size={13} className="ml-1 inline" /></button></div>
      </aside>
    </div>
  </div>
}
