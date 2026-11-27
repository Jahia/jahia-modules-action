import assert from 'node:assert/strict'
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'

import { prefetchIssue } from '../src/prefetch-issue.mjs'

// A GitHub client that answers every call with an empty, well-formed result.
const fakeGithub = () => ({
  rest: {
    issues: {
      get: async () => ({
        data: {
          title: 'A title',
          html_url: 'https://github.com/Jahia/sandbox/issues/1',
          state: 'open',
          user: { login: 'someone' },
          created_at: '2026-01-02T03:04:05Z',
          labels: [],
          assignees: [],
          body: 'A description',
        },
      }),
      listComments: 'issues.listComments',
    },
    pulls: {},
  },
  paginate: async () => [],
})

// Run the prefetch with an event file holding `event` (or no file at all when null).
const run = async (event) => {
  const dir = mkdtempSync(join(tmpdir(), 'prefetch-'))
  const eventPath = join(dir, 'event.json')
  if (event !== null) writeFileSync(eventPath, JSON.stringify(event))
  const contextDir = join(dir, 'context')
  const result = await prefetchIssue({
    github: fakeGithub(),
    contextDir,
    owner: 'Jahia',
    repo: 'sandbox',
    issueNumber: 1,
    eventPath,
  })
  return { result, contextDir, readme: readFileSync(join(contextDir, 'README.md'), 'utf8') }
}

test('writes trigger.md for an issue_comment event', async () => {
  const { contextDir, readme, result } = await run({
    comment: { id: 42, user: { login: 'someone' }, created_at: '2026-01-02T03:04:05Z', body: '@jahia-ai please fix' },
  })
  const trigger = readFileSync(join(contextDir, 'trigger.md'), 'utf8')
  assert.match(trigger, /Author: someone · posted 2026-01-02 03:04:05 UTC · id 42/)
  assert.match(trigger, /@jahia-ai please fix/)
  assert.match(readme, /`trigger\.md`/)
  assert.deepEqual(result, { fetched: 3, failed: 0 })
})

test('writes no trigger.md for a workflow_dispatch event, and records no failure', async () => {
  // A dispatch event carries no comment: the prompt is the request, so there is nothing to
  // index, and the absence must not be reported as a fetch failure.
  const { contextDir, readme, result } = await run({ inputs: { payload: '{}', prompt: 'do it' } })
  assert.equal(existsSync(join(contextDir, 'trigger.md')), false)
  assert.doesNotMatch(readme, /trigger\.md/)
  assert.doesNotMatch(readme, /Could not be fetched/)
  assert.deepEqual(result, { fetched: 2, failed: 0 })
})

test('records a failure, and no trigger.md, when the event file is unreadable', async () => {
  const { contextDir, readme, result } = await run(null)
  assert.equal(existsSync(join(contextDir, 'trigger.md')), false)
  assert.match(readme, /Could not be fetched/)
  assert.match(readme, /`trigger\.md`:/)
  assert.equal(result.failed, 1)
})

test('falls back on placeholders when the comment lacks author and body', async () => {
  const { contextDir } = await run({ comment: { id: 7 } })
  const trigger = readFileSync(join(contextDir, 'trigger.md'), 'utf8')
  assert.match(trigger, /Author: \? · posted \? · id 7/)
  assert.match(trigger, /\(the event carried no comment body\)/)
})
