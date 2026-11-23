import type { InterventionComparison, InterventionStrategy } from '../api/types'

// Summary values captured from engine.interventions.compare_interventions on the demo network for S1.
const strategyMetrics = {
  none: {
    impact_score: 0.243773,
    nodes_disrupted: ['ST1', 'ST2', 'ST3', 'ST5', 'ST6', 'WH1', 'WH3'],
    critical_shortages: ['ST1'], overloaded_nodes: [], estimated_recovery_time_h: 115,
    intervention_cost: 0, relative_impact_vs_baseline: 1,
    reasoning: ['No intervention supply was applied'], node_impacts: {},
  },
  reroute: {
    impact_score: 0.167665,
    nodes_disrupted: ['S2', 'ST1', 'ST2', 'ST3', 'ST6', 'WH1', 'WH3'],
    critical_shortages: ['ST1'], overloaded_nodes: ['S2'], estimated_recovery_time_h: 115,
    intervention_cost: 0, relative_impact_vs_baseline: 0.687792,
    reasoning: ['Alternate S2 exceeded spare capacity by 10 units; its downstream flow is exposed', 'Alternate S2 covered 20 units at WH1', 'Alternate S3 covered 6.825 units at WH2', 'Alternate WH2 covered 9 units at ST1', 'Alternate WH2 covered 4.2 units at ST5'], node_impacts: {},
  },
  backup_supplier: {
    impact_score: 0.23641,
    nodes_disrupted: ['ST1', 'ST2', 'ST3', 'ST5', 'ST6', 'WH1', 'WH3'],
    critical_shortages: ['ST1'], overloaded_nodes: [], estimated_recovery_time_h: 115,
    intervention_cost: 0, relative_impact_vs_baseline: 0.969796,
    reasoning: ['Temporary backup covered 5.25 units at ST6 after 12h'], node_impacts: {},
  },
  prioritize: {
    impact_score: 0.167665,
    nodes_disrupted: ['S2', 'ST1', 'ST2', 'ST3', 'ST6', 'WH1', 'WH3'],
    critical_shortages: ['ST1'], overloaded_nodes: ['S2'], estimated_recovery_time_h: 115,
    intervention_cost: 0, relative_impact_vs_baseline: 0.687792,
    reasoning: ['Alternate S2 exceeded spare capacity by 10 units; its downstream flow is exposed', 'Alternate S2 covered 20 units at WH1', 'Alternate S3 covered 6.825 units at WH2', 'Alternate WH2 covered 9 units at ST1', 'Priority policy allocated supply to critical node ST1 before non-critical destinations', 'Alternate WH2 covered 4.2 units at ST5'], node_impacts: {},
  },
} satisfies Record<InterventionStrategy, InterventionComparison['scenarios'][InterventionStrategy]>

export const demoInterventionComparison: InterventionComparison = {
  scenarios: strategyMetrics,
  recommended_strategy: 'prioritize',
  ranking: ['prioritize', 'reroute', 'backup_supplier', 'none'],
  recommendation_reason: 'Selected prioritize: lowest weighted impact, then recovery time, then intervention cost.',
}
