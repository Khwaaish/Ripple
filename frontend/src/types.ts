export type SectionId = 'Overview' | 'System Map' | 'Scenario Creator' | 'Ripple Simulation' | 'Intervention Center' | 'AI Analyst'

export type NavItem = {
  label: SectionId
  icon: string
  group: 'workspace' | 'insights'
}
