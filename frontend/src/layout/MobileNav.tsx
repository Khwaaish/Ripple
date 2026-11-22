import { Activity, Bot, GitBranch, LayoutDashboard, Network, ShieldCheck } from 'lucide-react'
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

export function MobileNav({ active, onNavigate }: { active: SectionId; onNavigate: (section: SectionId) => void }) {
  return <nav className="fixed inset-x-0 bottom-0 z-40 hidden border-t border-line bg-[#0d1016]/95 px-2 pb-[max(8px,env(safe-area-inset-bottom))] pt-2 backdrop-blur-lg max-sm:flex" aria-label="Mobile navigation">
    {items.map(({ label, icon: Icon }) => <button key={label} onClick={() => onNavigate(label)} aria-current={active === label ? 'page' : undefined} className={`mobile-nav-item ${active === label ? 'mobile-nav-active' : ''}`}><Icon size={17} /><span>{label === 'Ripple Simulation' ? 'Simulate' : label === 'Scenario Creator' ? 'Create' : label === 'Intervention Center' ? 'Actions' : label === 'Overview' ? 'Home' : label === 'System Map' ? 'Map' : 'Analyst'}</span></button>)}
  </nav>
}
