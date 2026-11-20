import { compact } from '../src/summarize/compact'
import { traceRun } from '../src/summarize/traceRun'

describe('compact', () => {
  it('joins whitespace and cuts at the limit', () => {
    expect(compact('a  b\n c')).toBe('a b c')
    expect(compact('abcdef', 3)).toBe('abc…')
    expect(compact({ a: 1 })).toBe('{"a":1}')
  })
})

describe('traceRun', () => {
  it('traces the init, the messages, the tools and the result', () => {
    const trace = traceRun(
      [
        { type: 'system', subtype: 'init', model: 'opus', cwd: '/w' },
        {
          type: 'assistant',
          message: {
            content: [
              { type: 'text', text: 'judging the ticket' },
              { type: 'tool_use', name: 'Write', input: { path: 'f.json' } },
            ],
          },
        },
        {
          type: 'result',
          subtype: 'success',
          num_turns: 4,
          duration_ms: 2500,
          total_cost_usd: 0.1234,
          result: 'done',
        },
      ],
      'batch 1',
      '0',
    )
    expect(trace.lines).toContain('[init] model=opus cwd=/w')
    expect(trace.lines).toContain('[say ] judging the ticket')
    expect(trace.lines).toContain('[tool] Write {"path":"f.json"}')
    expect(trace.outcome).toBe('success')
    expect(trace.turns).toBe('4')
    expect(trace.duration).toBe('3s')
    expect(trace.cost).toBe('0.1234')
  })

  it('reports a run with no result event as a crash', () => {
    const trace = traceRun([], 'batch 1', '137')
    expect(trace.outcome).toBe('no result (crash/kill)')
    expect(trace.lines).toContain('[end ] no result event found, agent exit code 137')
    expect(trace.result).toBeNull()
  })

  it('marks an error result', () => {
    const trace = traceRun(
      [{ type: 'result', subtype: 'error_max_turns', is_error: true }],
      'b',
      '1',
    )
    expect(trace.outcome).toBe('error (error_max_turns)')
    expect(trace.turns).toBe('n/a')
  })
})
