import { renderStateBlock } from '../src/state/renderStateBlock'
import { sampleState } from './fixtures'

describe('renderStateBlock', () => {
  it('keeps both markers and the state JSON on a single line', () => {
    const body = renderStateBlock(sampleState())
    expect(body).toContain('<!-- cortex-issue-agent-status -->')
    const lines = body.split('\n')
    const jsonLine = lines[lines.indexOf('<!-- cortex-issue-agent-state') + 1]
    expect(() => {
      JSON.parse(jsonLine ?? '')
    }).not.toThrow()
  })

  it('summarizes an in-flight session and the budget', () => {
    const body = renderStateBlock(sampleState())
    expect(body).toContain('Session #1 in progress')
    expect(body).toContain('Budget used: 1m 35s of 2h 00m')
  })

  it('summarizes a finished session once the lock is released', () => {
    const state = sampleState({
      lock: null,
      sessions: [
        {
          runId: 42,
          runUrl: 'https://github.com/Jahia/sandbox/actions/runs/42',
          trigger: 'assigned',
          startedAt: '2026-10-23T14:00:00.000Z',
          endedAt: '2026-10-23T14:05:00.000Z',
          seconds: 300,
          outcome: 'success',
        },
      ],
    })
    const body = renderStateBlock(state)
    expect(body).toContain('Session #1 finished (success) — 5m 00s')
  })

  it('notes an exhausted budget', () => {
    const body = renderStateBlock(
      sampleState({ budgetExhaustedNotedAt: '2026-10-23T16:00:00.000Z', lock: null }),
    )
    expect(body).toContain('budget for this issue is exhausted')
  })

  it('rejects a state whose serialization would break the HTML comment', () => {
    const bad = sampleState({
      lock: {
        runId: 42,
        runUrl: 'https://example.com/a-->b',
        lockedAt: '2026-10-23T14:00:00.000Z',
      },
    })
    expect(() => renderStateBlock(bad)).toThrow('-->')
  })
})
