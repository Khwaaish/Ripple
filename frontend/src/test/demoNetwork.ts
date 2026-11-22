import type { SupplyNetwork } from '../api/types'

const facilities: SupplyNetwork['nodes'] = [
  { id: 'S1', type: 'supplier', capacity: 150, load: 115, buffer_hours: 0, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'S2', type: 'supplier', capacity: 120, load: 100, buffer_hours: 0, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'S3', type: 'supplier', capacity: 100, load: 75, buffer_hours: 0, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'WH1', type: 'warehouse', capacity: 110, load: 100, buffer_hours: 8, critical: false, criticality_weight: 1, recovery_hours: 24, unit_cost: null },
  { id: 'WH2', type: 'warehouse', capacity: 130, load: 105, buffer_hours: 12, critical: false, criticality_weight: 1, recovery_hours: 18, unit_cost: null },
  { id: 'WH3', type: 'warehouse', capacity: 100, load: 70, buffer_hours: 6, critical: false, criticality_weight: 1, recovery_hours: 20, unit_cost: null },
  { id: 'ST1', type: 'store', capacity: 35, load: 30, buffer_hours: 4, critical: true, criticality_weight: 3, recovery_hours: 8, unit_cost: null },
  { id: 'ST2', type: 'store', capacity: 30, load: 24, buffer_hours: 8, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'ST3', type: 'store', capacity: 32, load: 27, buffer_hours: 3, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'ST4', type: 'store', capacity: 28, load: 22, buffer_hours: 10, critical: true, criticality_weight: 3, recovery_hours: 6, unit_cost: null },
  { id: 'ST5', type: 'store', capacity: 25, load: 20, buffer_hours: 5, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
  { id: 'ST6', type: 'store', capacity: 30, load: 25, buffer_hours: 12, critical: false, criticality_weight: 1, recovery_hours: 0, unit_cost: null },
]

const routes: SupplyNetwork['edges'] = ([
  ['S1', 'WH1', .7, 2, 80, false], ['S2', 'WH1', .3, 3, 40, true],
  ['S2', 'WH2', .65, 2, 90, false], ['S3', 'WH2', .35, 4, 50, true],
  ['S1', 'WH3', .35, 3, 40, false], ['S3', 'WH3', .65, 2, 70, false],
  ['WH1', 'ST1', .7, 1, 30, false], ['WH2', 'ST1', .3, 2, 20, true],
  ['WH1', 'ST2', 1, 1, 30, false], ['WH2', 'ST3', .7, 1, 30, false],
  ['WH3', 'ST3', .3, 2, 15, true], ['WH2', 'ST4', 1, 1, 28, false],
  ['WH3', 'ST5', .6, 1, 20, false], ['WH2', 'ST5', .4, 2, 15, true],
  ['WH3', 'ST6', .7, 1, 25, false], ['WH1', 'ST6', .3, 2, 15, true],
 ] as const).map(([src, dst, share, delay_h, capacity, is_alt]) => ({
  src: String(src), dst: String(dst), share: Number(share), delay_h: Number(delay_h),
  capacity: Number(capacity), reliability: 1, is_alt: Boolean(is_alt),
}))

export const demoNetworkFixture: SupplyNetwork = { nodes: facilities, edges: routes }
