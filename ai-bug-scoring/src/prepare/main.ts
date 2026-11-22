import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import * as core from '@actions/core'
import * as github from '@actions/github'
import type { Bug } from '../types'
import { batchKeys } from './batchKeys'
import { buildPrompt } from './buildPrompt'
import { fetchTicket } from './fetchTicket'
import { toTicket } from './toTicket'

// prepare entry point, run inside the composite action: the rubric and the tickets land in the
// log directory, one prompt per batch, so the agent needs no network and no GitHub token.
const run = async (): Promise<void> => {
  const env = process.env
  const bugs = JSON.parse(env.BUGS_JSON ?? '[]') as Bug[]
  const marker = env.MARKER ?? ''
  const batchSize = Number(env.BATCH_SIZE ?? '10')
  const logDir = join(env.RUNNER_TEMP ?? '.', 'bug-scoring-logs')
  const octokit = github.getOctokit(env.GH_TOKEN ?? '')

  for (const sub of ['tickets', 'factors']) mkdirSync(join(logDir, sub), { recursive: true })
  // The agent reads only under the log directory, so the rubric is copied there, with the reach
  // & importance list that the rubric names next to it. An older cortex ref has no list.
  const assets = join(env.CORTEX_PATH ?? '', '.claude/skills/jahia-pm-bug-scoring/assets')
  copyFileSync(join(assets, 'rubric.md'), join(logDir, 'rubric.md'))
  if (existsSync(join(assets, 'reach.md'))) {
    copyFileSync(join(assets, 'reach.md'), join(logDir, 'reach.md'))
  }
  writeFileSync(join(logDir, 'selected-bugs.json'), JSON.stringify(bugs, null, 2))

  const fetched: string[] = []
  for (const bug of bugs) {
    try {
      const ticket = toTicket(bug, await fetchTicket(octokit, bug.repository, bug.number), marker)
      writeFileSync(join(logDir, 'tickets', `${bug.key}.json`), JSON.stringify(ticket, null, 1))
      fetched.push(bug.key)
    } catch (error) {
      // The bug keeps its empty field, so the next run tries it again.
      core.warning(
        `${bug.repository}#${String(bug.number)}: could not read the ticket (${String(error)})`,
      )
    }
  }

  const template = readFileSync(join(env.GITHUB_ACTION_PATH ?? '.', 'prompt.md'), 'utf8')
  const groups = batchKeys(fetched, batchSize)
  groups.forEach((group, index) => {
    const listing = group
      .map(
        (key) =>
          `- \`${join(logDir, 'tickets', `${key}.json`)}\` → \`${join(logDir, 'factors', `${key}.json`)}\``,
      )
      .join('\n')
    const prompt = buildPrompt(template, {
      RUBRIC: join(logDir, 'rubric.md'),
      COUNT: String(group.length),
      TICKETS: listing,
    })
    writeFileSync(join(logDir, `batch-${String(index + 1)}.prompt.md`), prompt)
  })

  core.info(
    `Fetched: ${fetched.length > 0 ? fetched.join(' ') : 'none'}; ${String(groups.length)} agent run(s)`,
  )
  core.setOutput('logs_dir', logDir)
  core.setOutput('batches', String(groups.length))
}

void run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
