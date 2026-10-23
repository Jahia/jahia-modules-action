import { closeSession } from '../src/finalize/closeSession'
import { sampleState } from './fixtures'

const nowIso = '2026-10-23T14:10:00.000Z'

describe('closeSession', () => {
  it('releases its own lock, closes the session entry and grows the ledger', () => {
    const next = closeSession({
      state: sampleState(),
      runId: 42,
      runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
      seconds: 600,
      outcome: 'success',
      nowIso,
    })
    expect(next.lock).toBeNull()
    expect(next.ledgerSeconds).toBe(95 + 600)
    expect(next.sessions[0]).toMatchObject({ endedAt: nowIso, seconds: 600, outcome: 'success' })
  })

  it('never releases a lock held by another run', () => {
    const foreignLock = {
      runId: 99,
      runUrl: 'https://github.com/Jahia/sandbox/actions/runs/99',
      lockedAt: '2026-10-23T14:00:00.000Z',
    }
    const next = closeSession({
      state: sampleState({ lock: foreignLock }),
      runId: 42,
      runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
      seconds: 600,
      outcome: 'failure',
      nowIso,
    })
    expect(next.lock).toEqual(foreignLock)
    expect(next.sessions[0]?.outcome).toBe('failure')
  })

  it('reconstructs a closed entry when the session entry was lost with the state', () => {
    const next = closeSession({
      state: sampleState({ sessions: [], lock: null }),
      runId: 42,
      runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
      seconds: 120,
      outcome: 'cancelled',
      nowIso,
    })
    expect(next.sessions).toHaveLength(1)
    expect(next.sessions[0]).toMatchObject({
      trigger: 'unknown',
      seconds: 120,
      outcome: 'cancelled',
      endedAt: nowIso,
    })
    expect(next.ledgerSeconds).toBe(95 + 120)
  })
})
