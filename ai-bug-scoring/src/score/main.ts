import { appendFileSync } from 'node:fs'
import * as core from '@actions/core'
import * as github from '@actions/github'
import { applyScores } from './applyScores'
import { renderScoreSummary } from './renderScoreSummary'
import { runFailure } from './runFailure'

// apply-scores entry point, run inside the composite action once the agent recorded the factors.
const run = async (): Promise<void> => {
  const env = process.env
  const dryRun = env.DRY_RUN === 'true'
  const results = await applyScores(
    {
      comments: github.getOctokit(env.GH_TOKEN ?? ''),
      fields: github.getOctokit(env.FIELD_TOKEN ?? ''),
    },
    {
      logDir: env.LOG_DIR ?? '',
      dryRun,
      marker: env.MARKER ?? '',
      agent: env.AGENT ?? 'Claude Code',
      runUrl: env.RUN_URL ?? '',
      date: new Date().toISOString().slice(0, 10),
      warn: (message) => {
        core.warning(message)
      },
    },
  )
  for (const result of results) {
    core.info(
      `${result.ref}: ${result.outcome} ${result.value === undefined ? '' : String(result.value)}`,
    )
  }
  if (env.GITHUB_STEP_SUMMARY) {
    appendFileSync(env.GITHUB_STEP_SUMMARY, renderScoreSummary(results, !dryRun))
  }
  const failure = runFailure(results, dryRun)
  if (failure) core.setFailed(failure)
}

void run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
