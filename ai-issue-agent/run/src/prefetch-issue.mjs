import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

// Fetch everything the agent needs to read, before the agent starts: every fetch the agent
// makes costs a turn, and the ones its allowlist refuses cost far more. Best-effort by
// design — a session missing one context file is worth more than no session, so a failed
// fetch is recorded in the index the agent reads, not raised.
//
// On a pull request the issue files hold its conversation tab, and two more files hold what
// the issues API cannot serve: the branches and changed files, and the review threads.
export const prefetchIssue = async ({
  github,
  contextDir,
  owner,
  repo,
  issueNumber,
  eventPath,
  isPullRequest = false,
}) => {
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

  if (isPullRequest) {
    try {
      const { data: pull } = await github.rest.pulls.get({ owner, repo, pull_number: issueNumber })
      const files = await github.paginate(github.rest.pulls.listFiles, {
        owner,
        repo,
        pull_number: issueNumber,
        per_page: 100,
      })
      writeFileSync(
        join(contextDir, 'pull-request.md'),
        [
          `# Pull request ${owner}/${repo}#${issueNumber}`,
          '',
          `- State: ${pull.merged ? 'merged' : pull.state}${pull.draft ? ' (draft)' : ''}`,
          `- Head branch: \`${pull.head.ref}\` at ${pull.head.sha} (${pull.head.repo?.full_name ?? '?'})`,
          `- Base branch: \`${pull.base.ref}\``,
          `- Requested reviewers: ${(pull.requested_reviewers ?? []).map((r) => r.login).join(', ') || '(none)'}`,
          `- Changes: ${pull.commits} commit(s), +${pull.additions} −${pull.deletions} in ${pull.changed_files} file(s)`,
          '',
          '## Changed files',
          '',
          ...files.map((f) => `- \`${f.filename}\` — ${f.status}, +${f.additions} −${f.deletions}`),
          '',
          'The diff itself: `gh pr diff` on this pull request.',
          '',
        ].join('\n'),
      )
      index.push([
        'pull-request.md',
        'branches, head commit and changed files of the pull request this session works',
      ])
    } catch (error) {
      failures.push(['pull-request.md', String(error).split('\n')[0]])
    }

    try {
      const reviews = await github.paginate(github.rest.pulls.listReviews, {
        owner,
        repo,
        pull_number: issueNumber,
        per_page: 100,
      })
      const threads = await github.paginate(github.rest.pulls.listReviewComments, {
        owner,
        repo,
        pull_number: issueNumber,
        per_page: 100,
      })
      const rendered = [
        ...reviews
          .filter((review) => (review.body ?? '').trim() !== '' || review.state !== 'COMMENTED')
          .map((review) =>
            [
              `## Review · ${review.user?.login ?? '?'} · ${review.state} · ${stamp(review.submitted_at)} · id ${review.id}`,
              '',
              review.body || '(no summary)',
              '',
            ].join('\n'),
          ),
        ...threads.map((comment) =>
          [
            `## Inline · ${comment.user?.login ?? '?'} · ${stamp(comment.created_at)} · \`${comment.path}:${comment.line ?? comment.original_line ?? '?'}\` · id ${comment.id}${comment.in_reply_to_id ? ` · reply to ${comment.in_reply_to_id}` : ''}`,
            '',
            comment.body ?? '',
            '',
          ].join('\n'),
        ),
      ]
      writeFileSync(
        join(contextDir, 'reviews.md'),
        rendered.length ? rendered.join('\n') : 'No reviews yet.\n',
      )
      index.push([
        'reviews.md',
        `the reviews and inline review comments of the pull request (${reviews.length} review(s), ${threads.length} inline)`,
      ])
    } catch (error) {
      failures.push(['reviews.md', String(error).split('\n')[0]])
    }
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
