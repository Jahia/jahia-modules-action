import type { BugResult } from '../types'

// A write run that wrote nothing is a dead duty — a wrong token or a revoked scope would stay
// green forever — so the caller fails and its status output carries the message.
export const runFailure = (results: BugResult[], dryRun: boolean): string | null =>
  !dryRun && results.length > 0 && !results.some((result) => result.written)
    ? 'no PM Score field was written: every bug was skipped or every write failed — the job summary has each reason'
    : null
