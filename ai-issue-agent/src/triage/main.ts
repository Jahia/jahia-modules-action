import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import * as core from '@actions/core'
import * as github from '@actions/github'
import { buildContext, readEvent } from './context'
import { dispatchWorkflow } from './dispatch'
import type { DispatchPlan } from './plan'
import { planDispatch } from './plan'
import { runDecide } from './runDecide'

// triage-dispatch entry point: the guard admitted a session, and this step decides how it runs and
// starts it as a dispatched workflow. It never fails the job. Whatever goes wrong, the output
// `dispatched` stays false, and the inline agent job of the workflow runs the session on today's
// parameters, so a wrong or failed triage costs no more than the path it replaces.
//
// The one thing that must not happen is two sessions. So `dispatched` is set the moment the
// dispatch call succeeds, before anything that can still fail, such as the summary.

const summarize = async (plan: DispatchPlan, facts: Record<string, string>): Promise<void> => {
  await core.summary
    .addRaw(
      [
        '### AI agent triage',
        '',
        '| Parameter | Value |',
        '| -- | -- |',
        ...Object.entries(facts).map(([key, value]) => `| ${key} | ${value} |`),
        `| prompt length | ${String(plan.prompt.length)} characters |`,
        '',
      ].join('\n'),
    )
    .write()
}

const run = async (): Promise<void> => {
  core.setOutput('dispatched', 'false')
  try {
    const cortexPath = core.getInput('cortex_path', { required: true })
    const token = core.getInput('github_token', { required: true })
    const kind = core.getInput('target') === 'pull_request' ? 'pull_request' : 'issue'
    const budgetSeconds = Number(core.getInput('budget_seconds') || '60')
    const timeoutJobMinutes = Number(core.getInput('timeout_job') || '65')
    const workflow = core.getInput('dispatch_workflow') || 'delivery-ai-agent.yml'
    const repository = process.env.GITHUB_REPOSITORY ?? ''

    // event_path lets a test feed a synthetic event. A real run reads the event of the workflow.
    const eventPath = core.getInput('event_path') || (process.env.GITHUB_EVENT_PATH ?? '')
    const parsed = readEvent(JSON.parse(readFileSync(eventPath, 'utf8')) as unknown, kind)
    // The proof of concept runs where the request was made. A decision may name another
    // repository, and it is logged, but nothing runs there until the check of write access exists.
    if (parsed.origin.repo.toLowerCase() !== repository.toLowerCase()) {
      throw new Error(`the thread is in ${parsed.origin.repo}, not in ${repository}`)
    }

    const remainingSeconds = Number(core.getInput('remaining_seconds'))
    const directory = join(cortexPath, 'scratchpad', 'jahia-ai-triage')
    mkdirSync(directory, { recursive: true })
    const contextPath = join(directory, 'context.json')
    writeFileSync(contextPath, JSON.stringify(buildContext(parsed, remainingSeconds)))

    const started = Date.now()
    const result = await runDecide({
      command: join(cortexPath, 'tools', 'jahia-ai-triage', 'bin', 'jahia-ai-triage'),
      args: [
        'decide',
        '--context',
        contextPath,
        '--budget-seconds',
        String(budgetSeconds),
        '--log',
        join(directory, 'decisions.ndjson'),
      ],
      cwd: cortexPath,
      // The tool holds the budget. This is the second line, a little above it.
      timeoutMs: (budgetSeconds + 30) * 1000,
    })
    const triageSeconds = Math.round((Date.now() - started) / 1000)
    if (!result.ok) core.warning(`The triage gave no decision: ${result.reason}`)

    const plan = planDispatch({
      decision: result.ok ? result.decision : null,
      origin: parsed.origin,
      request: { author: parsed.author, body: parsed.request },
      guardRunId: Number(process.env.GITHUB_RUN_ID ?? '0'),
      sessionIndex: Number(core.getInput('session_index') || '1'),
      remainingSeconds,
      timeoutJobMinutes,
      defaultModel: core.getInput('model') || 'opus',
      cortexRef: core.getInput('cortex_ref') || 'main',
      owner: process.env.GITHUB_REPOSITORY_OWNER ?? '',
      serverUrl: process.env.GITHUB_SERVER_URL ?? 'https://github.com',
    })

    await dispatchWorkflow({
      octokit: github.getOctokit(token),
      repository,
      workflow,
      ref: parsed.defaultBranch,
      payload: plan.payload,
      prompt: plan.prompt,
    })
    core.setOutput('dispatched', 'true')

    const runner = JSON.stringify(plan.payload.runner)
    core.setOutput('source', plan.source)
    core.setOutput('runner', runner)
    core.setOutput('timeout_minutes', String(plan.payload.timeout_minutes))
    core.setOutput('model', String(plan.payload.model))
    core.setOutput('triage_seconds', String(triageSeconds))
    core.notice(
      `Dispatched ${workflow} on ${runner}, ${String(plan.payload.timeout_minutes)} min, ${String(plan.payload.model)} (${plan.source})`,
    )

    try {
      const decision = result.ok ? result.decision : null
      await summarize(plan, {
        source: plan.source,
        note: plan.note === '' ? '(none)' : plan.note,
        runner: `\`${runner}\``,
        timeout_minutes: `\`${String(plan.payload.timeout_minutes)}\``,
        model: `\`${String(plan.payload.model)}\``,
        persona: `\`${decision?.persona ?? 'none'}\``,
        decided_execution_repo: `\`${decision?.execution_repo ?? 'none'}\``,
        reason: decision?.reason ?? 'none',
        triage_seconds: String(triageSeconds),
        session_index: String(plan.payload.session_index),
        remaining_seconds: String(plan.payload.remaining_seconds),
      })
    } catch (error) {
      core.warning(`The triage summary was not written: ${String(error)}`)
    }
  } catch (error) {
    core.warning(
      `Not dispatched, so the session runs inline on today's parameters: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

void run()
