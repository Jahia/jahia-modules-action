import { STATE_MARKER_CLOSE, STATE_MARKER_OPEN } from './markers'
import type { AgentState } from './types'

// Null on any defect — a hand-edited or corrupt block must never crash the guard; the
// caller treats null as "no state yet" and rebuilds from scratch.
export const parseStateBlock = (body: string): AgentState | null => {
  const open = body.indexOf(STATE_MARKER_OPEN)
  if (open === -1) return null
  const start = open + STATE_MARKER_OPEN.length
  const end = body.indexOf(STATE_MARKER_CLOSE, start)
  if (end === -1) return null
  try {
    const parsed: unknown = JSON.parse(body.slice(start, end).trim())
    if (typeof parsed !== 'object' || parsed === null) return null
    const candidate = parsed as Record<string, unknown>
    if (
      candidate.version !== 1 ||
      typeof candidate.budgetSeconds !== 'number' ||
      typeof candidate.ledgerSeconds !== 'number' ||
      !Array.isArray(candidate.sessions)
    ) {
      return null
    }
    return candidate as unknown as AgentState
  } catch {
    return null
  }
}
