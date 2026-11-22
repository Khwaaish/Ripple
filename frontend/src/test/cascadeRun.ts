import type { ScenarioRun, SimulationResult } from '../api/types'
import { demoNetworkFixture } from './demoNetwork'

// Captured from engine.simulate(create_sample_network(), ["S1"]) for UI tests.
const supplierFailure: SimulationResult = {
  failed_nodes: ['S1'],
  directly_impacted_nodes: ['WH1', 'WH3'],
  second_order_impacted_nodes: ['ST1', 'ST2', 'ST3', 'ST5', 'ST6'],
  third_order_impacted_nodes: [],
  further_impacted_nodes: [],
  all_impacted_nodes: ['ST1', 'ST2', 'ST3', 'ST5', 'ST6', 'WH1', 'WH3'],
  overloaded_nodes: [],
  critical_shortage_nodes: ['ST1'],
  bottleneck_node: 'WH1',
  first_predicted_stockout_time_h: 9,
  propagation_rounds: 3,
  impact_score: 0.243773,
  severity: 'medium',
  round_snapshots: [
    { round: 1, newly_impacted: ['WH1', 'WH3'], losses: { S1: 115, WH1: 70, WH3: 24.5 }, overloaded_nodes: [] },
    { round: 2, newly_impacted: ['ST1', 'ST2', 'ST3', 'ST5', 'ST6'], losses: { S1: 115, ST1: 14.7, ST2: 16.8, ST3: 2.835, ST5: 4.2, ST6: 11.375, WH1: 70, WH3: 24.5 }, overloaded_nodes: [] },
    { round: 3, newly_impacted: [], losses: { S1: 115, ST1: 14.7, ST2: 16.8, ST3: 2.835, ST5: 4.2, ST6: 11.375, WH1: 70, WH3: 24.5 }, overloaded_nodes: [] },
  ],
  node_impacts: {},
  recovery_estimate_h: 115,
  intervention: 'none',
  intervention_cost: 0,
  reasoning: ['No intervention supply was applied'],
}

const storeFailureWithoutCascade: SimulationResult = {
  ...supplierFailure,
  failed_nodes: ['ST1'],
  directly_impacted_nodes: [],
  second_order_impacted_nodes: [],
  third_order_impacted_nodes: [],
  further_impacted_nodes: [],
  all_impacted_nodes: [],
  critical_shortage_nodes: [],
  bottleneck_node: null,
  first_predicted_stockout_time_h: null,
  propagation_rounds: 1,
  impact_score: 0,
  severity: 'low',
  round_snapshots: [{ round: 1, newly_impacted: [], losses: { ST1: 30 }, overloaded_nodes: [] }],
  node_impacts: {},
  recovery_estimate_h: 38,
}

export const supplierCascadeRun: ScenarioRun = { network: demoNetworkFixture, result: supplierFailure }
export const noCascadeRun: ScenarioRun = { network: demoNetworkFixture, result: storeFailureWithoutCascade }
