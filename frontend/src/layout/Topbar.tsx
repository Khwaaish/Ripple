import { Bell, ChevronDown, Command, Search, SlidersHorizontal } from 'lucide-react'
import type { SectionId } from '../types'

export function Topbar({ title }: { title: SectionId }) {
  return (
    <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between gap-4 border-b border-line bg-ink/85 px-8 backdrop-blur-xl max-md:px-5 max-sm:pl-5">
      <div className="flex items-center gap-3">
        <div className="hidden text-xs text-slate-600 md:block">Workspace <span className="mx-2 text-slate-700">/</span></div>
        <h1 className="text-sm font-medium text-slate-200">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <button className="search-button max-sm:hidden"><Search size={15} /><span>Search anything</span><kbd><Command size={10} /> K</kbd></button>
        <button aria-label="Filter workspace" className="toolbar-button"><SlidersHorizontal size={16} /></button>
        <button aria-label="Notifications" className="toolbar-button relative"><Bell size={17} /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-mint" /></button>
        <div className="mx-1 h-7 w-px bg-line max-sm:hidden" />
        <button className="hidden items-center gap-2 rounded-lg border border-line bg-panel px-3 py-2 text-xs text-slate-300 sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-mint shadow-[0_0_8px_rgba(88,214,176,.7)]" /> Pacific NW <ChevronDown size={13} className="text-slate-500" />
        </button>
      </div>
    </header>
  )
}
