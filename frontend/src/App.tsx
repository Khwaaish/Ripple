import { useState } from 'react'
import { ChevronRight, Database, Wifi } from 'lucide-react'
import { Sidebar } from './layout/Sidebar'
import { Topbar } from './layout/Topbar'
import { MobileNav } from './layout/MobileNav'
import { OverviewPage } from './pages/OverviewPage'
import { SystemMapPage } from './pages/SystemMapPage'
import { ScenarioCreatorPage } from './pages/ScenarioCreatorPage'
import { SimulationPage } from './pages/SimulationPage'
import { InterventionCenterPage } from './pages/InterventionCenterPage'
import { AIAnalystPage } from './pages/AIAnalystPage'
import type { SectionId } from './types'

function PageContent({ section, onNavigate }: { section: SectionId; onNavigate: (section: SectionId) => void }) {
  switch (section) {
    case 'Overview': return <OverviewPage onNavigate={onNavigate} />
    case 'System Map': return <SystemMapPage />
    case 'Scenario Creator': return <ScenarioCreatorPage />
    case 'Ripple Simulation': return <SimulationPage />
    case 'Intervention Center': return <InterventionCenterPage />
    case 'AI Analyst': return <AIAnalystPage />
  }
}

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionId>('Overview')
  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <Sidebar active={activeSection} onNavigate={setActiveSection} />
      <div className="min-h-screen pl-[248px] max-lg:pl-[76px] max-sm:pl-0">
        <Topbar title={activeSection} />
        <main className="mx-auto max-w-[1600px] px-8 py-7 max-lg:px-6 max-md:px-5 max-sm:px-4 max-sm:pb-24">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line/80 bg-panel/60 px-4 py-3">
            <div className="flex items-center gap-2 text-xs"><span className="flex h-7 w-7 items-center justify-center rounded-lg border border-mint/10 bg-mint/[.06] text-mint"><Database size={14} /></span><div><span className="font-medium text-slate-300">Pacific Northwest network</span><span className="mx-2 text-slate-700">·</span><span className="text-slate-500">Demo workspace</span></div><ChevronRight size={13} className="text-slate-700" /></div>
            <div className="flex items-center gap-4 text-[10px] text-slate-600"><span className="flex items-center gap-1.5"><span className="status-dot status-dot-green" /> Engine status <strong className="font-medium text-slate-400">Operational</strong></span><span className="hidden items-center gap-1.5 sm:flex"><Wifi size={12} /> Mock data · API not connected</span></div>
          </div>
          <PageContent section={activeSection} onNavigate={setActiveSection} />
          <footer className="flex items-center justify-between border-t border-line/70 py-4 text-[10px] text-slate-700 max-sm:hidden"><span>Ripple Network Intelligence <span className="mx-1.5">·</span> Prototype workspace</span><span>Last updated just now</span></footer>
        </main>
      </div>
      <MobileNav active={activeSection} onNavigate={setActiveSection} />
    </div>
  )
}
