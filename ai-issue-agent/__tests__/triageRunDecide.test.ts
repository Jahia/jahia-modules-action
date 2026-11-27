import { chmodSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { isDecision, runDecide } from '../src/triage/runDecide'

const DECISION = {
  version: 1,
  outcome: 'decision',
  fallback_reason: null,
  origin: { repo: 'Jahia/sandbox', number: 721, kind: 'issue', comment_id: 99 },
  persona: 'devops',
  runner: 'default',
  expected_minutes: 10,
  buffer_minutes: 15,
  timeout_minutes: 25,
  execution_repo: 'Jahia/sandbox',
  model_complexity: 'simple',
  model: 'haiku',
  prompt_brief: 'A short task.',
  reason: 'Short.',
}

// The decision without one field.
const without = (field: string): Record<string, unknown> =>
  Object.fromEntries(Object.entries(DECISION).filter(([key]) => key !== field))

// A throwaway program that stands for the tool, so the test starts no model.
const program = (body: string): { command: string; directory: string } => {
  const directory = mkdtempSync(join(tmpdir(), 'triage-tool-'))
  const command = join(directory, 'tool')
  writeFileSync(command, `#!/bin/sh\n${body}\n`)
  chmodSync(command, 0o755)
  return { command, directory }
}

const json = (value: unknown): string => `printf '%s' '${JSON.stringify(value)}'`

describe('runDecide', () => {
  it('returns the decision that the tool printed', async () => {
    const { command, directory } = program(json(DECISION))
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 5000 })
    expect(result).toEqual({ ok: true, decision: DECISION })
  })

  it('passes the arguments and runs in the directory it was given', async () => {
    const { command, directory } = program(
      `printf '%s' "$(printf '%s' '${JSON.stringify(DECISION)}' | sed "s|Short.|$* in $(pwd)|")"`,
    )
    const result = await runDecide({
      command,
      args: ['decide', '--context', 'c.json'],
      cwd: directory,
      timeoutMs: 5000,
    })
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.decision.reason).toContain('decide --context c.json')
      expect(result.decision.reason).toContain(directory.replace(/^\/private/, ''))
    }
  })

  it('reports an exit status other than zero, with the last line of stderr', async () => {
    const { command, directory } = program("echo 'first' >&2; echo 'refused: not JSON' >&2; exit 2")
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 5000 })
    expect(result).toEqual({ ok: false, reason: 'the triage exited 2: refused: not JSON' })
  })

  it('reports an output that is not JSON', async () => {
    const { command, directory } = program('echo not json')
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 5000 })
    expect(result).toEqual({ ok: false, reason: 'the triage printed no JSON object' })
  })

  it('reports a decision that lacks a field the dispatch reads', async () => {
    const { command, directory } = program(json(without('runner')))
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 5000 })
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.reason).toContain('lacks a field')
  })

  it('cuts a tool that outlives its wall clock, and does not wait for it', async () => {
    const { command, directory } = program('sleep 30')
    const started = Date.now()
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 400 })
    expect(Date.now() - started).toBeLessThan(5000)
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.reason).toContain('passed its wall clock')
  })

  it('cuts the children of the tool with it', async () => {
    // The shell starts a child and waits for it. Killing the shell alone would leave the child
    // holding the pipe open, and the run would end only when the child did.
    const { command, directory } = program('sleep 30 & wait')
    const started = Date.now()
    const result = await runDecide({ command, args: [], cwd: directory, timeoutMs: 400 })
    expect(Date.now() - started).toBeLessThan(5000)
    expect(result.ok).toBe(false)
  })

  it('reports a program that cannot start', async () => {
    const result = await runDecide({
      command: '/nonexistent/jahia-ai-triage',
      args: [],
      cwd: tmpdir(),
      timeoutMs: 5000,
    })
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.reason).toContain('did not start')
  })
})

describe('isDecision', () => {
  it('accepts a decision and a fallback', () => {
    expect(isDecision(DECISION)).toBe(true)
    expect(
      isDecision({
        ...DECISION,
        outcome: 'fallback',
        fallback_reason: 'session_failed',
        persona: null,
      }),
    ).toBe(true)
  })

  it.each([
    'outcome',
    'origin',
    'runner',
    'timeout_minutes',
    'model',
    'prompt_brief',
    'reason',
    'execution_repo',
  ])('refuses a decision without %s', (field) => {
    expect(isDecision(without(field))).toBe(false)
  })

  it.each([
    ['an unknown runner', { runner: 'huge' }],
    ['an unknown model', { model: 'gpt' }],
    ['a timeout that is a string', { timeout_minutes: '25' }],
    ['an origin without a comment id', { origin: { repo: 'a/b', number: 1, kind: 'issue' } }],
  ])('refuses %s', (_name, override) => {
    expect(isDecision({ ...DECISION, ...override })).toBe(false)
  })

  it('refuses what is not an object', () => {
    expect(isDecision(null)).toBe(false)
    expect(isDecision([DECISION])).toBe(false)
    expect(isDecision('decision')).toBe(false)
  })
})
