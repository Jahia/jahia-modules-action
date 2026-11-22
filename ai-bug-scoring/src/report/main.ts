import { appendFileSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import * as core from '@actions/core'
import type { BugResult } from '../types'
import { renderScoreSummary } from './renderScoreSummary'
import { runFailure } from './runFailure'

// report entry point, run once the jahia-pm-score tool of the cortex checkout scored the bugs and
// wrote results.json: the job summary, and the healthcheck that fails a write run that wrote nothing.
const run = (): void => {
  const env = process.env
  const dryRun = env.DRY_RUN === 'true'
  const results = JSON.parse(
    readFileSync(join(env.LOG_DIR ?? '', 'results.json'), 'utf8'),
  ) as BugResult[]
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

try {
  run()
} catch (error) {
  core.setFailed(error instanceof Error ? error.message : String(error))
}
