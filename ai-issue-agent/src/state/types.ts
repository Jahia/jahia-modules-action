// 'assigned' is historical: only a mention triggers a session now, but ledgers written
// before that change may still carry assignment-triggered entries.
export type TriggerKind = 'assigned' | 'mentioned'
export type SessionOutcome = 'success' | 'failure' | 'cancelled'

export interface SessionEntry {
  runId: number
  runUrl: string
  // 'unknown' only on an entry reconstructed by finalize after the state was lost mid-run
  trigger: TriggerKind | 'unknown'
  startedAt: string
  endedAt: string | null
  seconds: number | null
  outcome: SessionOutcome | null
}

export interface AgentLock {
  runId: number
  runUrl: string
  lockedAt: string
}

export interface AgentState {
  version: 1
  budgetSeconds: number
  // Only ever grows; the guard refuses a session once it reaches budgetSeconds
  ledgerSeconds: number
  firstRunAt: string
  // Set when the one-time exhaustion note was written; later refusals stay silent
  budgetExhaustedNotedAt: string | null
  lock: AgentLock | null
  sessions: SessionEntry[]
}
