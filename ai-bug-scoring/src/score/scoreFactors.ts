import type { Factors, ScoreRow } from '../types'
import {
  CLEAR,
  CLOUD,
  IMPACT,
  MAX_CUSTOMERS,
  OLDER,
  PER_CUSTOMER,
  REACH,
  REGRESSION,
  WORKAROUND,
} from './tables'

const capitalize = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1)

// Return the points and the rows of the breakdown of one bug. The labels decide the customer gate
// and back the cloud and regression flags the agent may have missed.
export const scoreFactors = (
  factors: Factors,
  labels: string[],
): { points: number; rows: ScoreRow[] } => {
  const customerLabel = labels.includes('customer')
  const customers = customerLabel ? Math.min(MAX_CUSTOMERS, Math.max(1, factors.customers)) : 0
  const cloud = factors.cloud || labels.includes('cloud')
  const regression = factors.regression || labels.includes('regression')
  const [impactPoints, impactLabel] = IMPACT[factors.impact] ?? [0, factors.impact]
  const [reachPoints, reachLabel] = REACH[factors.reach] ?? [0, factors.reach]
  const rows: ScoreRow[] = [
    { name: 'Impact', text: impactLabel, points: impactPoints },
    {
      name: 'Reach & importance',
      text: `${reachLabel} (${factors.feature})`,
      points: reachPoints,
    },
    {
      name: 'Workaround',
      text: capitalize(factors.workaround),
      points: WORKAROUND[factors.workaround] ?? 0,
    },
    { name: 'Regression', text: regression ? 'Yes' : 'No', points: regression ? REGRESSION : 0 },
    {
      name: 'Customers',
      text: customerLabel ? String(customers) : 'No customer label',
      points: PER_CUSTOMER * customers,
    },
    {
      name: 'Expected behaviour clear',
      text: factors.clear ? 'Yes' : 'No',
      points: factors.clear ? CLEAR : 0,
    },
    { name: 'Jahia Cloud', text: cloud ? 'Yes' : 'No', points: cloud ? CLOUD : 0 },
    {
      name: 'Only older versions',
      text: factors.older_version_only ? 'Yes' : 'No',
      points: factors.older_version_only ? OLDER : 0,
    },
  ]
  return { points: rows.reduce((sum, row) => sum + row.points, 0), rows }
}
