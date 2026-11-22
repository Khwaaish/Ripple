export const metrics = [
  { label: 'Network health', value: '94.2%', change: '+2.4%', detail: 'vs. last 7 days', icon: 'Activity', tone: 'mint' },
  { label: 'Active facilities', value: '12 / 12', change: 'All online', detail: 'across 3 tiers', icon: 'Boxes', tone: 'blue' },
  { label: 'At-risk nodes', value: '03', change: '1 critical', detail: 'require attention', icon: 'ShieldAlert', tone: 'amber' },
  { label: 'Avg. recovery time', value: '18.6h', change: '−3.2h', detail: 'from baseline', icon: 'Timer', tone: 'violet' },
]

export const events = [
  { title: 'Alternate route capacity restored', location: 'Warehouse WH-02 → Store ST-04', time: '12 min ago', status: 'Resolved', tone: 'mint' },
  { title: 'Supplier delay detected', location: 'Supplier SUP-01 · Pacific Northwest', time: '38 min ago', status: 'Monitoring', tone: 'amber' },
  { title: 'Weekly resilience simulation complete', location: 'Scenario: Regional port disruption', time: '2 hours ago', status: 'Complete', tone: 'blue' },
]

export const exposedTiers = [
  { name: 'Suppliers', count: '3 facilities', health: 96, color: 'bg-mint' },
  { name: 'Warehouses', count: '3 facilities', health: 91, color: 'bg-sky-400' },
  { name: 'Retail stores', count: '6 facilities', health: 94, color: 'bg-violet-400' },
]

export const watchlist = [
  { id: 'SUP-01', name: 'Northstar Components', type: 'Supplier', risk: 'Elevated', tone: 'amber', score: '72' },
  { id: 'WH-02', name: 'Portland Distribution', type: 'Warehouse', risk: 'Guarded', tone: 'blue', score: '48' },
  { id: 'ST-04', name: 'Seattle Central', type: 'Store', risk: 'Stable', tone: 'mint', score: '21' },
]

export const strategies = [
  { title: 'Reroute', tag: 'Network-aware', text: 'Shift demand through alternate inbound routes with available spare capacity.', impact: '−31%', color: 'mint' },
  { title: 'Backup supplier', tag: 'Time-bound', text: 'Activate temporary backup supply after the configured response window.', impact: '−24%', color: 'blue' },
  { title: 'Prioritize', tag: 'Critical-first', text: 'Allocate constrained alternate flow to critical destinations first.', impact: '−18%', color: 'violet' },
]
