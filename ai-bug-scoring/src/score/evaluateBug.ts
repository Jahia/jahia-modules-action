import type { Bug, BugResult, Factors, Ticket } from '../types'
import { checkFactors } from './checkFactors'
import { renderComment } from './renderComment'
import { scoreFactors } from './scoreFactors'
import { SECURITY_VALUE } from './tables'

// Return the result of one bug: its value, its comment, or the reason it is skipped. A security
// bug gets no comment, because one on a public repository would disclose it.
export const evaluateBug = (
  bug: Bug,
  ticket: Ticket | Error,
  factors: unknown,
  { marker, agent, runUrl, date }: { marker: string; agent: string; runUrl: string; date: string },
): BugResult => {
  const ref = `${bug.repository}#${String(bug.number)}`
  const base = { ref, key: bug.key, url: bug.url }
  if (ticket instanceof Error) return { ...base, outcome: 'skipped', reason: 'ticket not fetched' }
  if (factors instanceof Error) {
    return { ...base, outcome: 'skipped', reason: `no factors (${factors.name})` }
  }
  const problems = checkFactors(factors, ref)
  if (problems.length > 0) {
    return { ...base, outcome: 'skipped', reason: `invalid factors: ${problems.join('; ')}` }
  }
  const valid = factors as Factors
  if (valid.security) return { ...base, outcome: 'security', value: SECURITY_VALUE }
  const { points, rows } = scoreFactors(valid, ticket.labels)
  const comment = renderComment({ marker, points, rows, factors: valid, agent, runUrl, date })
  return {
    ...base,
    outcome: 'scored',
    value: points,
    points,
    impact: valid.impact,
    reach: valid.reach,
    customers: valid.customers,
    confidence: valid.confidence,
    comment,
  }
}
