import type { Factors } from '../types'
import { CONFIDENCE, IMPACT, REACH, WORKAROUND } from './tables'

const KEYS: Record<keyof Factors, 'string' | 'boolean' | 'number'> = {
  ref: 'string',
  security: 'boolean',
  impact: 'string',
  feature: 'string',
  reach: 'string',
  workaround: 'string',
  regression: 'boolean',
  clear: 'boolean',
  cloud: 'boolean',
  older_version_only: 'boolean',
  customers: 'number',
  confidence: 'string',
  why: 'string',
}

// Return the list of problems of one factors object; an empty list means it can be scored.
export const checkFactors = (factors: unknown, ref: string): string[] => {
  if (typeof factors !== 'object' || factors === null || Array.isArray(factors)) {
    return ['not a JSON object']
  }
  const record = factors as Record<string, unknown>
  const problems: string[] = []
  for (const [key, kind] of Object.entries(KEYS)) {
    const value = record[key]
    // A customers count must be a whole number: a float or a boolean is a mistake, not a count.
    if (typeof value !== kind || (kind === 'number' && !Number.isInteger(value))) {
      problems.push(
        `${key}: expected ${kind === 'number' ? 'int' : kind}, got ${JSON.stringify(value)}`,
      )
    }
  }
  if (problems.length > 0) return problems
  const typed = record as unknown as Factors
  if (typed.ref !== ref) problems.push(`ref: expected ${ref}, got ${typed.ref}`)
  const allowed: [string, string[]][] = [
    ['impact', Object.keys(IMPACT)],
    ['reach', Object.keys(REACH)],
    ['workaround', Object.keys(WORKAROUND)],
    ['confidence', [...CONFIDENCE]],
  ]
  for (const [key, values] of allowed) {
    const value = record[key] as string
    if (!values.includes(value)) {
      problems.push(
        `${key}: ${JSON.stringify(value)} is not one of ${JSON.stringify([...values].sort())}`,
      )
    }
  }
  if (typed.customers < 0) problems.push(`customers: ${String(typed.customers)} is negative`)
  return problems
}
