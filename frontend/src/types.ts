export type SectionId = 'Overview' | 'System Map' | 'Scenario Creator' | 'Ripple Simulation' | 'Intervention Center' | 'AI Analyst' | 'Adaption Showcase'

export type NavItem = {
  label: SectionId
  icon: string
  group: 'workspace' | 'insights'
}
