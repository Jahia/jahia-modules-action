import { spawn } from 'node:child_process'
import type { Decision } from './plan'

// Runs `jahia-ai-triage decide` as a child under a hard wall clock, and returns the decision it
// printed. The tool holds its own budget. This wall clock is the second line: a tool that hangs
// before it starts its own clock, or a child that outlives it, still ends here, because the job
// has a few minutes to live and a stuck triage must fall through to the inline session.

export interface RunDecideOptions {
  command: string
  args: string[]
  cwd: string
  timeoutMs: number
  env?: NodeJS.ProcessEnv
}

export type DecideResult = { ok: true; decision: Decision } | { ok: false; reason: string }

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isOrigin = (value: unknown): boolean =>
  isRecord(value) &&
  typeof value.repo === 'string' &&
  Number.isInteger(value.number) &&
  (value.kind === 'issue' || value.kind === 'pull_request') &&
  Number.isInteger(value.comment_id)

// The tool validates a decision against its schema before it prints it. This guard checks only
// the fields that the dispatch reads, so a change of the tool that drops one stops here.
export const isDecision = (value: unknown): value is Decision =>
  isRecord(value) &&
  (value.outcome === 'decision' || value.outcome === 'fallback') &&
  isOrigin(value.origin) &&
  typeof value.runner === 'string' &&
  Number.isInteger(value.timeout_minutes) &&
  (value.model === 'haiku' || value.model === 'sonnet' || value.model === 'opus') &&
  typeof value.prompt_brief === 'string' &&
  typeof value.reason === 'string' &&
  typeof value.execution_repo === 'string'

export const runDecide = (options: RunDecideOptions): Promise<DecideResult> =>
  new Promise((resolve) => {
    let stdout = ''
    let stderr = ''
    let settled = false
    const finish = (result: DecideResult): void => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve(result)
    }

    // detached: the child leads its own process group, so the kill below reaches what it started.
    const child = spawn(options.command, options.args, {
      cwd: options.cwd,
      env: options.env ?? process.env,
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    const timer = setTimeout(() => {
      try {
        if (child.pid !== undefined) process.kill(-child.pid, 'SIGKILL')
      } catch {
        // The group is already gone.
      }
      finish({
        ok: false,
        reason: `the triage passed its wall clock of ${String(options.timeoutMs / 1000)}s`,
      })
    }, options.timeoutMs)

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf8')
    })
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf8')
    })
    child.on('error', (error) => {
      finish({ ok: false, reason: `the triage did not start: ${error.message}` })
    })
    child.on('close', (code) => {
      if (code !== 0) {
        finish({
          ok: false,
          reason: `the triage exited ${String(code)}: ${stderr.trim().split('\n').slice(-1)[0] ?? ''}`,
        })
        return
      }
      let parsed: unknown
      try {
        parsed = JSON.parse(stdout)
      } catch {
        finish({ ok: false, reason: 'the triage printed no JSON object' })
        return
      }
      if (!isDecision(parsed)) {
        finish({
          ok: false,
          reason: 'the triage printed a decision that lacks a field the dispatch reads',
        })
        return
      }
      finish({ ok: true, decision: parsed })
    })
  })
