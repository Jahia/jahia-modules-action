import { readFileSync } from 'node:fs'
import * as core from '@actions/core'
import * as github from '@actions/github'
import { findStatusComment } from '../state/findStatusComment'
import { parseStateBlock } from '../state/parseStateBlock'
import { renderStateBlock } from '../state/renderStateBlock'
import type { AgentState, SessionEntry } from '../state/types'
import { evaluateTrigger } from './evaluateTrigger'
import type { TriggerEvent } from './evaluateTrigger'
import { isLockStale } from './isLockStale'

// check-request entry point: decides whether an agent session is owed, takes the lock and
// bootstraps or updates the overall-status comment. Everything here is deterministic — no
// model call. The workflow-level concurrency group serializes this guard per issue, which
// is what makes the read-modify-write on the comment safe; the comment is its durable
// record.
const run = async (): Promise<void> => {
  const token = core.getInput('github_token', { required: true })
  const repository = core.getInput('repository') || (process.env.GITHUB_REPOSITORY ?? '')
  const issueNumber = Number(core.getInput('issue_number', { required: true }))
  const agentLogin = core.getInput('agent_login') || 'jahia-ai'
  const budgetSeconds = Number(core.getInput('budget_seconds') || '7200')
  const timeoutJobMinutes = Number(core.getInput('timeout_job') || '30')
  const [owner = '', repo = ''] = repository.split('/')
  const key = `${repository}#${String(issueNumber)}`

  // The event payload is read from disk, never passed through an action input: a comment
  // body flowing through a `${{ }}` expression would be a script-injection surface.
  const eventName = process.env.GITHUB_EVENT_NAME ?? ''
  const payload = JSON.parse(
    readFileSync(process.env.GITHUB_EVENT_PATH ?? '', 'utf8'),
  ) as TriggerEvent['payload']

  const evaluation = evaluateTrigger({ eventName, payload, agentLogin })
  if (!evaluation.qualifies || evaluation.trigger === undefined) {
    core.setOutput('eligible', 'false')
    core.notice(`${key}: skipping — ${evaluation.reason ?? 'the event does not qualify'}`)
    return
  }

  const octokit = github.getOctokit(token)
  const comment = await findStatusComment(octokit, { owner, repo, issueNumber })
  const state = comment ? parseStateBlock(comment.body) : null
  if (comment && !state) {
    core.warning(
      `${key}: the status comment exists but its state block is missing or corrupt — rebuilding the state`,
    )
  }

  const now = new Date()
  if (state?.lock) {
    if (!isLockStale(state.lock, now.getTime(), timeoutJobMinutes)) {
      core.setOutput('eligible', 'false')
      core.notice(
        `${key}: an agent session is already in flight (${state.lock.runUrl}) — silently prevented`,
      )
      return
    }
    core.warning(`${key}: reclaiming a stale lock held by ${state.lock.runUrl}`)
  }

  if (state && comment && state.ledgerSeconds >= state.budgetSeconds) {
    core.setOutput('eligible', 'false')
    core.notice(
      `${key}: refusing — the issue's agent budget is exhausted (${String(state.ledgerSeconds)}s of ${String(state.budgetSeconds)}s)`,
    )
    // == null: a pre-existing state block may simply lack the field (undefined at runtime)
    if (state.budgetExhaustedNotedAt == null) {
      // Note the exhaustion in the visible summary exactly once; later refusals stay silent.
      const noted: AgentState = { ...state, lock: null, budgetExhaustedNotedAt: now.toISOString() }
      await octokit.rest.issues.updateComment({
        owner,
        repo,
        comment_id: comment.id,
        body: renderStateBlock(noted),
      })
    }
    return
  }

  const base: AgentState = state ?? {
    version: 1,
    budgetSeconds,
    ledgerSeconds: 0,
    firstRunAt: now.toISOString(),
    budgetExhaustedNotedAt: null,
    lock: null,
    sessions: [],
  }
  const runId = Number(process.env.GITHUB_RUN_ID ?? '0')
  const runUrl = `${process.env.GITHUB_SERVER_URL ?? 'https://github.com'}/${repository}/actions/runs/${String(runId)}`
  const session: SessionEntry = {
    runId,
    runUrl,
    trigger: evaluation.trigger,
    startedAt: now.toISOString(),
    endedAt: null,
    seconds: null,
    outcome: null,
  }
  const next: AgentState = {
    ...base,
    lock: { runId, runUrl, lockedAt: now.toISOString() },
    sessions: [...base.sessions, session],
  }
  const body = renderStateBlock(next)
  let commentId: number
  if (comment) {
    await octokit.rest.issues.updateComment({ owner, repo, comment_id: comment.id, body })
    commentId = comment.id
  } else {
    const created = await octokit.rest.issues.createComment({
      owner,
      repo,
      issue_number: issueNumber,
      body,
    })
    commentId = created.data.id
  }
  // 👍 on the triggering comment: the visible sign that what it asks is being handled.
  // Only after the lock is taken, so a silently prevented duplicate stays traceless.
  if (evaluation.commentId !== undefined) {
    try {
      await octokit.rest.reactions.createForIssueComment({
        owner,
        repo,
        comment_id: evaluation.commentId,
        content: '+1',
      })
    } catch (error: unknown) {
      // The session matters more than the reaction: failing here would strand the lock.
      core.warning(
        `${key}: could not react to comment ${String(evaluation.commentId)} — ${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  const remaining = next.budgetSeconds - next.ledgerSeconds
  core.setOutput('eligible', 'true')
  core.setOutput('remaining_seconds', String(remaining))
  core.setOutput('session_index', String(next.sessions.length))
  core.setOutput('trigger', evaluation.trigger)
  core.setOutput('comment_id', String(commentId))
  core.info(
    `${key}: session #${String(next.sessions.length)} is owed (trigger: ${evaluation.trigger}, remaining budget: ${String(remaining)}s)`,
  )
}

void run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
