import { Activity, Bot, Boxes, ChevronDown, CircleHelp, Command, GitBranch, LayoutDashboard, Network, Settings2, ShieldCheck, Sparkles, Waypoints } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { SectionId } from '../types'

const items: { label: SectionId; icon: LucideIcon }[] = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'System Map', icon: Network },
  { label: 'Scenario Creator', icon: GitBranch },
  { label: 'Ripple Simulation', icon: Activity },
  { label: 'Intervention Center', icon: ShieldCheck },
  { label: 'AI Analyst', icon: Bot },
]

export function Sidebar({ active, onNavigate }: { active: SectionId; onNavigate: (section: SectionId) => void }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-[248px] flex-col border-r border-line bg-[#0d1016] max-lg:w-[76px] max-sm:hidden">
      <div className="flex h-[72px] items-center gap-3 border-b border-line px-5 max-lg:justify-center max-lg:px-0">
        <div className="brand-mark"><Waypoints size={20} strokeWidth={2.2} /></div>
        <div className="max-lg:hidden">
          <div className="text-[15px] font-semibold tracking-[0.16em] text-slate-100">RIPPLE</div>
          <div className="mt-0.5 text-[9px] font-semibold tracking-[0.19em] text-slate-500">NETWORK INTELLIGENCE</div>
        </div>
      </div>

      <div className="px-3 pt-6 max-lg:px-2">
        <p className="sidebar-label">WORKSPACE</p>
        <nav className="mt-2 space-y-1" aria-label="Primary navigation">
          {items.map(({ label, icon: Icon }) => {
            const selected = active === label
            return (
              <button
                key={label}
                onClick={() => onNavigate(label)}
                aria-current={selected ? 'page' : undefined}
                title={label}
                className={`nav-item ${selected ? 'nav-item-active' : ''}`}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span className="max-lg:hidden">{label}</span>
                {selected && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-mint max-lg:hidden" />}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="mt-8 px-3 max-lg:px-2">
        <p className="sidebar-label">SAVED VIEWS</p>
        <button className="nav-item text-slate-500" title="Critical node watch"><span className="ml-1 h-2 w-2 rounded-full bg-amber-400" /><span className="max-lg:hidden">Critical node watch</span></button>
        <button className="nav-item text-slate-500" title="Weekly resilience"><span className="ml-1 h-2 w-2 rounded-full bg-sky-400" /><span className="max-lg:hidden">Weekly resilience</span></button>
      </div>

      <div className="mt-auto px-3 pb-4 max-lg:px-2">
        <div className="mb-3 rounded-xl border border-line bg-[#11151c] p-3 max-lg:hidden">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300"><Sparkles size={14} className="text-mint" /> Intelligence layer</div>
          <p className="mt-2 text-[11px] leading-relaxed text-slate-500">AI Analyst is ready to summarize modeled outcomes.</p>
          <div className="mt-3 flex items-center gap-1.5 text-[10px] text-slate-400"><span className="status-dot status-dot-green" /> Engine operational</div>
        </div>
        <button className="nav-item text-slate-400" title="Help center"><CircleHelp size={17} /><span className="max-lg:hidden">Help center</span></button>
        <button className="nav-item text-slate-400" title="Settings"><Settings2 size={17} /><span className="max-lg:hidden">Settings</span></button>
        <div className="mt-3 flex items-center gap-2 border-t border-line pt-4 max-lg:justify-center">
          <div className="avatar">AR</div>
          <div className="min-w-0 flex-1 max-lg:hidden"><p className="truncate text-xs font-medium text-slate-200">Alex Rivera</p><p className="mt-0.5 text-[10px] text-slate-500">Operations lead</p></div>
          <ChevronDown size={14} className="text-slate-500 max-lg:hidden" />
        </div>
      </div>
    </aside>
  )
}
