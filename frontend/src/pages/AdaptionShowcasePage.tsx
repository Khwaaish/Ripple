import {
  ArrowRight,
  BadgeCheck,
  Brain,
  Check,
  CircleDot,
  Database,
  GitBranch,
  Layers3,
  ShieldCheck,
  Sparkles,
  Target,
  Waves,
} from 'lucide-react'
import { SectionHeading } from '../components/SectionHeading'

const training = [
  { label: 'Epochs', value: '8' },
  { label: 'Training steps', value: '184' },
  { label: 'Batch size', value: '1' },
  { label: 'LoRA rank', value: '32' },
  { label: 'LoRA alpha', value: '64' },
]

const pipeline = [
  { step: '01', title: 'Engine-labeled data', detail: '2,000 training scenarios', icon: Database, tone: 'text-sky-300 border-sky-300/15 bg-sky-300/[.06]' },
  { step: '02', title: 'Gemma 3 4B PT', detail: 'Pretrained base model', icon: Brain, tone: 'text-violet-300 border-violet-300/15 bg-violet-300/[.06]' },
  { step: '03', title: 'LoRA adaptation', detail: 'Adaption · rank 32', icon: Layers3, tone: 'text-mint border-mint/15 bg-mint/[.06]' },
  { step: '04', title: 'Ripple predictions', detail: 'Inference validation in progress', icon: Sparkles, tone: 'text-amber-200 border-amber-300/15 bg-amber-300/[.06]' },
  { step: '05', title: 'Simulation validation', detail: 'Compare with engine ground truth', icon: ShieldCheck, tone: 'text-slate-300 border-slate-500/20 bg-slate-400/[.05]' },
]

function EvidenceRate({ title, rate, detail, accent }: { title: string; rate: number; detail: string; accent: 'slate' | 'mint' }) {
  const adapted = accent === 'mint'
  return <div className={`rounded-xl border p-4 ${adapted ? 'border-mint/15 bg-mint/[.035]' : 'border-line bg-[#0d1117]'}`}>
    <div className="flex items-start justify-between gap-3">
      <div><p className="text-[10px] font-medium uppercase tracking-[.12em] text-slate-500">{title}</p><p className={`mt-2 text-3xl font-semibold tracking-tight ${adapted ? 'text-mint' : 'text-slate-200'}`}>{rate}%</p></div>
      <span className={`mt-1 rounded-full border px-2 py-1 text-[9px] ${adapted ? 'border-mint/15 bg-mint/[.06] text-mint' : 'border-slate-700 text-slate-500'}`}>{adapted ? 'Adapted' : 'Base'}</span>
    </div>
    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#242b35]" aria-label={`${title} training win rate: ${rate}%`}>
      <div className={`h-full rounded-full ${adapted ? 'bg-mint' : 'bg-slate-500'}`} style={{ width: `${rate}%` }} />
    </div>
    <p className="mt-2 text-[10px] text-slate-500">{detail}</p>
  </div>
}

export function AdaptionShowcasePage() {
  return <div className="space-y-5 pb-10">
    <SectionHeading
      title="Adaption showcase"
      description="A focused view of Ripple’s model adaptation, training evidence, and validation path."
      action={<span className="inline-flex items-center gap-2 rounded-md border border-mint/15 bg-mint/[.05] px-2.5 py-1.5 text-[10px] font-medium text-mint"><CircleDot size={12} /> Model program</span>}
    />

    <section className="relative overflow-hidden rounded-2xl border border-line bg-[#10161d] p-5 sm:p-7 lg:p-8">
      <div className="pointer-events-none absolute -right-16 -top-28 h-80 w-80 rounded-full bg-mint/[.055] blur-3xl" />
      <div className="relative grid gap-7 lg:grid-cols-[minmax(0,1.25fr)_minmax(260px,.75fr)] lg:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-2"><span className="rounded-md border border-mint/15 bg-mint/[.05] px-2 py-1 text-[9px] font-semibold uppercase tracking-[.14em] text-mint">Adaption · model adaptation</span><span className="text-[9px] uppercase tracking-[.12em] text-slate-600">Ripple intelligence layer</span></div>
          <h2 className="mt-4 max-w-2xl text-2xl font-semibold leading-tight tracking-[-.025em] text-slate-100 sm:text-3xl">Teaching a model to reason across cascading supply-chain failures.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">A network disruption is more than a failed facility. Ripple’s adaptation task asks the model to trace downstream tiers, distinguish propagation rounds, identify bottlenecks, and rank mitigation options from structured network inputs.</p>
          <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-amber-300/15 bg-amber-300/[.045] px-3 py-2 text-[11px] font-medium text-amber-100" role="status"><CircleDot size={13} className="text-amber-300" /> Inference validation in progress</div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-line bg-[#0c1117]/90 p-4"><div className="flex items-center gap-2 text-slate-500"><Brain size={15} /><span className="text-[9px] font-semibold uppercase tracking-[.13em]">Base model</span></div><p className="mt-3 text-sm font-semibold text-slate-100">Gemma 3 4B PT</p><p className="mt-1 text-[10px] text-slate-500">Pretrained foundation</p></div>
          <div className="rounded-xl border border-mint/15 bg-mint/[.035] p-4"><div className="flex items-center gap-2 text-mint"><Layers3 size={15} /><span className="text-[9px] font-semibold uppercase tracking-[.13em]">Adaptation</span></div><p className="mt-3 text-sm font-semibold text-slate-100">LoRA fine-tuning</p><p className="mt-1 text-[10px] text-slate-500">Parameter-efficient</p></div>
          <div className="col-span-2 flex items-center gap-3 rounded-xl border border-line bg-[#0c1117]/90 p-4"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-sky-300/15 bg-sky-300/[.06] text-sky-200"><Database size={16} /></div><div className="min-w-0 flex-1"><p className="text-[9px] font-semibold uppercase tracking-[.12em] text-slate-500">Dataset boundary</p><p className="mt-1 flex flex-wrap items-center gap-1 text-xs font-medium text-slate-200"><span>2,000 train</span><span className="mx-1 text-slate-700">/</span><span>300 held out</span></p></div><BadgeCheck size={15} className="text-slate-600" /></div>
        </div>
      </div>
    </section>

    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,.85fr)]">
      <section className="panel-card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="text-[9px] font-semibold uppercase tracking-[.14em] text-slate-600">Training evidence</p><h3 className="mt-1.5 text-sm font-semibold text-slate-200">PLATFORM-REPORTED TRAINING WIN RATES</h3></div>
          <span className="rounded-md border border-amber-300/15 bg-amber-300/[.04] px-2 py-1 text-[9px] font-medium text-amber-200">Training signal only</span>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <EvidenceRate title="Base win rate" rate={12} detail="Adaption-reported · base model" accent="slate" />
          <EvidenceRate title="Adapted win rate" rate={88} detail="Adaption-reported · after LoRA adaptation" accent="mint" />
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-mint/10 bg-mint/[.035] px-3.5 py-3"><div className="flex items-center gap-2 text-xs font-medium text-mint"><Target size={14} /> +76 percentage points</div><span className="text-[9px] text-slate-500">Difference between reported training rates</span></div>
        <p className="mt-3 text-[10px] leading-relaxed text-slate-500">These are <strong className="font-semibold text-slate-300">platform-reported training win rates, not held-out accuracy.</strong> The 300 held-out scenarios remain reserved for independent evaluation; no evaluation result is available here.</p>
      </section>

      <section className="panel-card p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3"><div><p className="text-[9px] font-semibold uppercase tracking-[.14em] text-slate-600">Run configuration</p><h3 className="mt-1.5 text-sm font-semibold text-slate-200">Parameter-efficient adaptation</h3></div><span className="rounded-md border border-line bg-[#0d1117] px-2 py-1 text-[9px] text-slate-500">LoRA</span></div>
        <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3">
          {training.map(({ label, value }) => <div key={label} className="rounded-lg border border-line bg-[#0d1117] p-3"><p className="text-[9px] text-slate-600">{label}</p><p className="mt-1.5 font-mono text-base font-semibold text-slate-200">{value}</p></div>)}
        </div>
        <div className="mt-4 flex items-start gap-2.5 border-t border-line pt-4"><Waves size={14} className="mt-0.5 shrink-0 text-sky-300" /><p className="text-[10px] leading-relaxed text-slate-500">LoRA adapts a focused set of model parameters for Ripple’s structured cascade-analysis task while retaining the Gemma base model.</p></div>
      </section>
    </div>

    <section className="panel-card overflow-hidden">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line px-5 py-4 sm:px-6"><div><p className="text-[9px] font-semibold uppercase tracking-[.14em] text-slate-600">Adaptation workflow</p><h3 className="mt-1.5 text-sm font-semibold text-slate-200">From deterministic labels to verified model behavior</h3></div><span className="text-[9px] text-slate-600">Training completed · inference validation pending</span></div>
      <div className="overflow-x-auto p-4 sm:p-5"><div className="flex min-w-[880px] items-stretch gap-2">
        {pipeline.map(({ step, title, detail, icon: Icon, tone }, index) => <div className="contents" key={step}>
          <article className="flex min-w-0 flex-1 flex-col rounded-xl border border-line bg-[#0d1117] p-3.5">
            <div className="flex items-center justify-between"><span className="text-[9px] font-mono text-slate-600">{step}</span><span className={`flex h-8 w-8 items-center justify-center rounded-lg border ${tone}`}><Icon size={15} /></span></div>
            <h4 className="mt-3 text-[11px] font-semibold text-slate-200">{title}</h4><p className="mt-1 text-[9px] leading-relaxed text-slate-500">{detail}</p>
          </article>
          {index < pipeline.length - 1 && <div className="flex shrink-0 items-center text-slate-700"><ArrowRight size={15} /></div>}
        </div>)}
      </div></div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line px-5 py-3 text-[9px] text-slate-600 sm:px-6"><span className="inline-flex items-center gap-1.5"><Check size={11} className="text-mint" /> Engine provides verified ground truth</span><span className="inline-flex items-center gap-1.5"><CircleDot size={11} className="text-amber-300" /> Model output validation is in progress</span></div>
    </section>

    <section className="grid gap-4 lg:grid-cols-2">
      <article className="rounded-xl border border-sky-300/10 bg-gradient-to-br from-sky-300/[.045] to-transparent p-5"><div className="flex items-center gap-2"><GitBranch size={15} className="text-sky-300" /><h3 className="text-xs font-semibold text-slate-200">Why adapt for cascade reasoning?</h3></div><p className="mt-3 text-[11px] leading-relaxed text-slate-400">Supply-chain failure analysis depends on connected structure and order: which facilities lose supply first, how shortages propagate across tiers, where bottlenecks emerge, and which mitigation strategy best limits modeled impact. Ripple’s adaptation focuses the model on that domain-specific response format.</p></article>
      <article className="rounded-xl border border-line bg-[#10151c] p-5"><div className="flex items-center gap-2"><ShieldCheck size={15} className="text-mint" /><h3 className="text-xs font-semibold text-slate-200">Validation guardrail</h3></div><p className="mt-3 text-[11px] leading-relaxed text-slate-400">The deterministic simulation remains the source of verified labels. Model-generated predictions will be checked against that reference only after inference validation; this showcase reports no held-out accuracy or successful prediction claims.</p><div className="mt-3 inline-flex items-center gap-1.5 text-[9px] font-medium text-amber-200"><CircleDot size={11} /> Evaluation not yet reported <ArrowRight size={11} /></div></article>
    </section>
  </div>
}
