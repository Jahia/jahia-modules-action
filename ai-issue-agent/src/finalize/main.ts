import * as core from '@actions/core'
import * as github from '@actions/github'
import { findStatusComment } from '../state/findStatusComment'
import { parseStateBlock } from '../state/parseStateBlock'
import { renderStateBlock } from '../state/renderStateBlock'
import type { AgentState, SessionOutcome } from '../state/types'
import { closeSession } from './closeSession'

// finalize entry point: releases the lock and writes the session's seconds into the
// ledger. Best-effort by contract — it runs with `if: always()` and must never fail the
// job; a finalize lost to a hard cancel is healed by the guard's stale-lock rule.
const run = async (): Promise<void> => {
  const token = core.getInput('github_token', { required: true })
  const repository = core.getInput('repository') || (process.env.GITHUB_REPOSITORY ?? '')
  const issueNumber = Number(core.getInput('issue_number', { required: true }))
  const startedEpoch = Number(core.getInput('session_started_epoch', { required: true }))
  const outcomeInput = core.getInput('outcome') || 'failure'
  const outcome: SessionOutcome =
    outcomeInput === 'success' || outcomeInput === 'cancelled' ? outcomeInput : 'failure'
  const [owner = '', repo = ''] = repository.split('/')
  const key = `${repository}#${String(issueNumber)}`

  const octokit = github.getOctokit(token)
  const comment = await findStatusComment(octokit, { owner, repo, issueNumber })
  const state = comment ? parseStateBlock(comment.body) : null
  const now = new Date()
  const runId = Number(process.env.GITHUB_RUN_ID ?? '0')
  const runUrl = `${process.env.GITHUB_SERVER_URL ?? 'https://github.com'}/${repository}/actions/runs/${String(runId)}`
  const seconds = Math.max(0, Math.round(now.getTime() / 1000 - startedEpoch))

  if (!state) {
    core.warning(
      `${key}: no state found at finalize (status comment deleted or corrupted mid-run) — recreating it from what this run knows`,
    )
  }
  const base: AgentState = state ?? {
    version: 1,
    budgetSeconds: 7200,
    ledgerSeconds: 0,
    firstRunAt: now.toISOString(),
    budgetExhaustedNotedAt: null,
    lock: null,
    sessions: [],
  }
  if (base.lock && base.lock.runId !== runId) {
    core.warning(
      `${key}: the lock is held by another run (${base.lock.runUrl}) — closing this session without touching it`,
    )
  }
  const next = closeSession({
    state: base,
    runId,
    runUrl,
    seconds,
    outcome,
    nowIso: now.toISOString(),
  })
  const body = renderStateBlock(next)
  if (comment) {
    await octokit.rest.issues.updateComment({ owner, repo, comment_id: comment.id, body })
  } else {
    await octokit.rest.issues.createComment({ owner, repo, issue_number: issueNumber, body })
  }
  core.info(
    `${key}: session finished (${outcome}) — ${String(seconds)}s; budget used ${String(next.ledgerSeconds)}s of ${String(next.budgetSeconds)}s`,
  )
}

void run().catch((error: unknown) => {
  // Never fail the job: finalize is best-effort, and the stale-lock rule is the backstop.
  core.warning(`finalize failed: ${error instanceof Error ? error.message : String(error)}`)
})
