import * as core from '@actions/core'
import * as github from '@actions/github'
import { selectBugs } from './selectBugs'

// select-bugs entry point: LLM-free selection, runs on any cheap runner and prints what it
// selected to the job summary. The outputs feed the ai-bug-scoring composite action.
const run = async (): Promise<void> => {
  const token = core.getInput('github_token', { required: true })
  const org = core.getInput('org') || 'Jahia'
  const searchScope = core.getInput('search_scope') || 'org:Jahia'
  const field = core.getInput('field') || 'PM Score'
  const maxBugs = Number(core.getInput('max_bugs') || '30')
  const octokit = github.getOctokit(token)

  const selection = await selectBugs(octokit, { org, searchScope, field, maxBugs })
  core.info(
    `${String(selection.selected.length)} bug(s) selected after ${String(selection.seen)} issue(s) seen and ${String(selection.read)} field read(s): ${selection.query}`,
  )
  for (const bug of selection.selected) core.info(`  - ${bug.repository}#${String(bug.number)}`)

  await core.summary
    .addHeading('Bug selection', 3)
    .addRaw(
      `\nSearch: \`${selection.query}\`, newest first — ${String(selection.seen)} issue(s) read; ` +
        `${String(selection.selected.length)} selected whose "${field}" field is empty ` +
        `(at most ${String(maxBugs)} per run).\n\n`,
    )
    .addTable([
      [{ data: 'Bug', header: true }],
      ...selection.selected.map((bug) => [`${bug.repository}#${String(bug.number)}`]),
    ])
    .write()

  core.setOutput('bugs', JSON.stringify(selection.selected))
  core.setOutput('has_bugs', selection.selected.length > 0 ? 'true' : 'false')
}

void run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
