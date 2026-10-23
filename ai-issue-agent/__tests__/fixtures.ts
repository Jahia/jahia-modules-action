import type { AgentState } from '../src/state/types'

export const sampleState = (overrides: Partial<AgentState> = {}): AgentState => ({
  version: 1,
  budgetSeconds: 7200,
  ledgerSeconds: 95,
  firstRunAt: '2026-10-23T14:00:00.000Z',
  budgetExhaustedNotedAt: null,
  lock: {
    runId: 42,
    runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
    lockedAt: '2026-10-23T14:00:00.000Z',
  },
  sessions: [
    {
      runId: 42,
      runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
      trigger: 'assigned',
      startedAt: '2026-10-23T14:00:00.000Z',
      endedAt: null,
      seconds: null,
      outcome: null,
    },
  ],
  ...overrides,
})
