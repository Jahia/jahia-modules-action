import { planDispatch } from '../src/triage/plan'
import type { Decision, PlanInput } from '../src/triage/plan'

const ORIGIN = { repo: 'Jahia/sandbox', number: 721, kind: 'issue' as const, comment_id: 99 }

const decision = (overrides: Partial<Decision> = {}): Decision => ({
  outcome: 'decision',
  origin: ORIGIN,
  persona: 'devops',
  runner: 'default',
  timeout_minutes: 30,
  execution_repo: 'Jahia/sandbox',
  model: 'sonnet',
  prompt_brief: 'Check the runner flavour and report the instance type.',
  reason: 'A short read-only task.',
  fallback_reason: null,
  ...overrides,
})

const input = (overrides: Partial<PlanInput> = {}): PlanInput => ({
  decision: decision(),
  origin: ORIGIN,
  request: { author: 'someone', body: '@jahia-ai please look at the runner' },
  guardRunId: 123456,
  sessionIndex: 2,
  remainingSeconds: 5400,
  timeoutJobMinutes: 65,
  defaultModel: 'opus',
  cortexRef: 'main',
  owner: 'Jahia',
  serverUrl: 'https://github.com',
  ...overrides,
})

describe('planDispatch, a decision', () => {
  it('turns the decision into the payload of the execution', () => {
    const plan = planDispatch(input())
    expect(plan.source).toBe('decision')
    expect(plan.note).toBe('')
    expect(plan.payload).toEqual({
      version: 1,
      runner: 'default',
      timeout_minutes: 30,
      model: 'sonnet',
      origin: { repository: 'Jahia/sandbox', number: 721, target: 'issue' },
      session_index: 2,
      remaining_seconds: 5400,
      guard_run_id: 123456,
      cortex_ref: 'main',
    })
  })

  it('passes a flavour the triage may pick by its name', () => {
    expect(planDispatch(input({ decision: decision({ runner: 'small' }) })).payload.runner).toBe(
      'small',
    )
  })

  it.each(['ubuntu-latest', 'ubuntu-slim', 'huge'])(
    'falls back to the defaults on the runner %p, which the triage may not pick',
    (runner) => {
      const plan = planDispatch(input({ decision: decision({ runner }) }))
      expect(plan.source).toBe('fallback')
      expect(plan.note).toContain('which the triage may not pick')
      expect(plan.payload.runner).toBe('default')
    },
  )

  it('names the pull request target for a pull request', () => {
    const origin = { ...ORIGIN, kind: 'pull_request' as const }
    const plan = planDispatch(input({ origin, decision: decision({ origin }) }))
    expect(plan.payload.origin).toEqual({
      repository: 'Jahia/sandbox',
      number: 721,
      target: 'pull_request',
    })
  })

  it('never exceeds the timeout of the guard', () => {
    const plan = planDispatch(
      input({ decision: decision({ timeout_minutes: 65 }), timeoutJobMinutes: 40 }),
    )
    expect(plan.payload.timeout_minutes).toBe(40)
  })

  it('keeps a timeout under the guard as it is', () => {
    expect(
      planDispatch(input({ decision: decision({ timeout_minutes: 20 }) })).payload.timeout_minutes,
    ).toBe(20)
  })

  it('never goes under the floor of the execution workflow', () => {
    expect(planDispatch(input({ timeoutJobMinutes: 3 })).payload.timeout_minutes).toBe(6)
  })

  it('states the whole remaining budget, rounded down', () => {
    expect(planDispatch(input({ remainingSeconds: 1234.9 })).payload.remaining_seconds).toBe(1234)
  })

  it('falls back on the timeout of the guard when the remaining budget is unknown', () => {
    expect(planDispatch(input({ remainingSeconds: Number.NaN })).payload.remaining_seconds).toBe(
      65 * 60,
    )
  })

  it('writes the persona as a hint, then the brief, then the request verbatim', () => {
    const { prompt } = planDispatch(input())
    expect(prompt).toContain('Persona hint: DevOps.')
    expect(prompt).toContain('take another profile if the request needs it')
    expect(prompt).toContain('Brief: Check the runner flavour and report the instance type.')
    expect(prompt).toContain('The request, verbatim (someone, comment 99):')
    expect(prompt.endsWith('@jahia-ai please look at the runner')).toBe(true)
  })

  it('leaves out the persona line when the decision names none', () => {
    const { prompt } = planDispatch(input({ decision: decision({ persona: null }) }))
    expect(prompt).not.toContain('Persona hint')
    expect(prompt.startsWith('Brief:')).toBe(true)
  })

  it('keeps the characters of the request that a shell or a template would read', () => {
    const body = '@jahia-ai run `rm -rf /` and ${{ secrets.X }} and $(id) and __NAME__'
    const { prompt } = planDispatch(input({ request: { author: 'someone', body } }))
    expect(prompt.endsWith(body)).toBe(true)
  })

  it('cuts a request that would pass the dispatch ceiling, and says so', () => {
    const { prompt } = planDispatch(
      input({ request: { author: 'someone', body: 'x'.repeat(40000) } }),
    )
    expect(prompt.length).toBeLessThan(31000)
    expect(prompt).toContain('[the request was cut here]')
  })
})

describe('planDispatch, the defaults of today', () => {
  it('runs the original request on the default parameters after a fallback', () => {
    const plan = planDispatch(
      input({
        decision: decision({
          outcome: 'fallback',
          fallback_reason: 'budget_exceeded',
          persona: null,
          prompt_brief: '',
          runner: 'small',
          timeout_minutes: 15,
          model: 'haiku',
        }),
      }),
    )
    expect(plan.source).toBe('fallback')
    expect(plan.note).toContain('budget_exceeded')
    expect(plan.payload.runner).toBe('default')
    expect(plan.payload.timeout_minutes).toBe(65)
    expect(plan.payload.model).toBe('opus')
    expect(plan.prompt.startsWith('The request, verbatim')).toBe(true)
    expect(plan.prompt).not.toContain('Brief:')
  })

  it('uses the defaults when the triage gave nothing', () => {
    const plan = planDispatch(input({ decision: null, defaultModel: 'sonnet' }))
    expect(plan.source).toBe('default')
    expect(plan.payload.runner).toBe('default')
    expect(plan.payload.model).toBe('sonnet')
    expect(plan.payload.timeout_minutes).toBe(65)
  })

  it('falls back when the decision fails the validation of the execution', () => {
    const plan = planDispatch(
      input({ decision: decision({ model: 'a model; rm -rf /' as Decision['model'] }) }),
    )
    expect(plan.source).toBe('fallback')
    expect(plan.note).toContain('fails the payload validation')
    expect(plan.payload.model).toBe('opus')
  })

  it('throws when even the default parameters would be refused', () => {
    // A thread of another owner: the execution refuses it, so nothing may be dispatched.
    const origin = { ...ORIGIN, repo: 'evil/repo' }
    expect(() => planDispatch(input({ origin, decision: null }))).toThrow('must belong to Jahia')
  })

  it('does not refuse an empty request, because the prompt still names the comment', () => {
    expect(() =>
      planDispatch(input({ request: { author: 'someone', body: '' }, decision: null })),
    ).not.toThrow()
  })
})
