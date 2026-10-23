import type { AgentLock } from '../state/types'

// A finalize that never ran (hard-cancelled job, dead runner) would otherwise deadlock the
// issue forever: past the job timeout plus a margin, the lock is reclaimable.
export const isLockStale = (lock: AgentLock, nowMs: number, timeoutJobMinutes: number): boolean =>
  nowMs - new Date(lock.lockedAt).getTime() > (timeoutJobMinutes + 10) * 60_000
