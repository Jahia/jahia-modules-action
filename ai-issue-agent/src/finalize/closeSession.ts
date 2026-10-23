import type { AgentState, SessionOutcome } from '../state/types'

export interface CloseSessionParams {
  state: AgentState
  runId: number
  runUrl: string
  seconds: number
  outcome: SessionOutcome
  nowIso: string
}

// Close this run's session entry and grow the ledger. The lock is released only when this
// run holds it: after a stale-lock reclaim, another session's lock must survive us. A
// session entry lost with the state (deleted comment) is reconstructed as already closed.
export const closeSession = ({
  state,
  runId,
  runUrl,
  seconds,
  outcome,
  nowIso,
}: CloseSessionParams): AgentState => {
  const ownsLock = state.lock?.runId === runId
  const hasEntry = state.sessions.some((entry) => entry.runId === runId && entry.endedAt === null)
  const sessions = hasEntry
    ? state.sessions.map((entry) =>
        entry.runId === runId && entry.endedAt === null
          ? { ...entry, endedAt: nowIso, seconds, outcome }
          : entry,
      )
    : [
        ...state.sessions,
        {
          runId,
          runUrl,
          trigger: 'unknown' as const,
          startedAt: nowIso,
          endedAt: nowIso,
          seconds,
          outcome,
        },
      ]
  return {
    ...state,
    sessions,
    ledgerSeconds: state.ledgerSeconds + seconds,
    lock: ownsLock ? null : state.lock,
  }
}
