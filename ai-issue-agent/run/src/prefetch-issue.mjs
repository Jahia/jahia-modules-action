import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

// Fetch everything the agent needs to read, before the agent starts: every fetch the agent
// makes costs a turn, and the ones its allowlist refuses cost far more. Best-effort by
// design — a session missing one context file is worth more than no session, so a failed
// fetch is recorded in the index the agent reads, not raised.
export const prefetchIssue = async ({ github, contextDir, owner, repo, issueNumber, eventPath }) => {
  mkdirSync(contextDir, { recursive: true })
  const index = []
  const failures = []
  const stamp = (date) => (date ? String(date).replace('T', ' ').replace('Z', ' UTC') : '?')

  try {
    const { data: issue } = await github.rest.issues.get({ owner, repo, issue_number: issueNumber })
    const labels = (issue.labels ?? [])
      .map((label) => (typeof label === 'string' ? label : label.name))
      .filter(Boolean)
    writeFileSync(
      join(contextDir, 'issue.md'),
      [
        `# ${issue.title}`,
        '',
        `- Issue: ${issue.html_url} (${issue.state})`,
        `- Author: ${issue.user?.login ?? '?'} · created ${stamp(issue.created_at)}`,
        `- Labels: ${labels.length ? labels.join(', ') : '(none)'}`,
        `- Assignees: ${(issue.assignees ?? []).map((a) => a.login).join(', ') || '(none)'}`,
        '',
        '## Description',
        '',
        issue.body ?? '(empty)',
        '',
      ].join('\n'),
    )
    index.push(['issue.md', 'title, metadata and full description of the issue'])
  } catch (error) {
    failures.push(['issue.md', String(error).split('\n')[0]])
  }

  try {
    const comments = await github.paginate(github.rest.issues.listComments, {
      owner,
      repo,
      issue_number: issueNumber,
      per_page: 100,
    })
    const rendered = comments.map((comment) =>
      [
        `## ${comment.user?.login ?? '?'} · ${stamp(comment.created_at)} · id ${comment.id}`,
        '',
        comment.body ?? '',
        '',
      ].join('\n'),
    )
    writeFileSync(
      join(contextDir, 'comments.md'),
      rendered.length ? rendered.join('\n') : 'No comments yet.\n',
    )
    index.push(['comments.md', `every issue comment, oldest first (${comments.length})`])
  } catch (error) {
    failures.push(['comments.md', String(error).split('\n')[0]])
  }

  try {
    const payload = JSON.parse(readFileSync(eventPath, 'utf8'))
    const trigger = payload.comment ?? {}
    writeFileSync(
      join(contextDir, 'trigger.md'),
      [
        '# The comment that started this session',
        '',
        `- Author: ${trigger.user?.login ?? '?'} · posted ${stamp(trigger.created_at)} · id ${trigger.id ?? '?'}`,
        '',
        trigger.body ?? '(the event carried no comment body)',
        '',
      ].join('\n'),
    )
    index.push(['trigger.md', 'the @-mention comment that started this session — the request to act on'])
  } catch (error) {
    failures.push(['trigger.md', String(error).split('\n')[0]])
  }

  const readme = [
    `# Pre-fetched context for ${owner}/${repo}#${issueNumber}`,
    '',
    'Fetched before the agent started. Read these instead of re-fetching:',
    '',
    ...index.map(([file, description]) => `- \`${file}\` — ${description}`),
  ]
  if (failures.length) {
    readme.push('', '## Could not be fetched', '')
    readme.push(...failures.map(([file, reason]) => `- \`${file}\`: ${reason}`))
  }
  writeFileSync(join(contextDir, 'README.md'), `${readme.join('\n')}\n`)
  return { fetched: index.length, failed: failures.length }
}
