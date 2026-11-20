import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { applyScores } from '../src/score/applyScores'
import { renderScoreSummary } from '../src/score/renderScoreSummary'
import { runFailure } from '../src/score/runFailure'
import type { BugResult, Octokit } from '../src/types'
import { FIELD_ID, MARKER, bug, factors } from './fixtures'

interface Call {
  route: string
  params: Record<string, unknown>
}

describe('applyScores', () => {
  let dir: string
  let sequence: Call[]
  let existingComments: { id: number; body: string }[]
  let fieldsReject: boolean
  let comments: Octokit
  let fields: Octokit

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'apply-scores-'))
    for (const sub of ['tickets', 'factors']) mkdirSync(join(dir, sub))
    // 1: scored; 2: a security bug; 3: the agent wrote no factors.
    const bugs = [bug(1), bug(2), bug(3)]
    writeFileSync(join(dir, 'selected-bugs.json'), JSON.stringify(bugs))
    for (const entry of bugs) {
      writeFileSync(
        join(dir, 'tickets', `${entry.key}.json`),
        JSON.stringify({ labels: ['customer'] }),
      )
    }
    writeFileSync(join(dir, 'factors', 'Jahia-example-1.json'), JSON.stringify(factors()))
    writeFileSync(
      join(dir, 'factors', 'Jahia-example-2.json'),
      JSON.stringify(factors({ ref: 'Jahia/example#2', security: true })),
    )
    sequence = []
    existingComments = [{ id: 7, body: `${MARKER}\nold score` }]
    fieldsReject = false
    comments = {
      request: jest.fn((route: string, params: Record<string, unknown>) => {
        sequence.push({ route, params })
        if (route.startsWith('GET')) return Promise.resolve({ data: existingComments, headers: {} })
        return Promise.resolve({})
      }),
    } as unknown as Octokit
    fields = {
      request: jest.fn((route: string, params: Record<string, unknown>) => {
        sequence.push({ route: `field ${route}`, params })
        return fieldsReject ? Promise.reject(new Error('field write refused')) : Promise.resolve({})
      }),
    } as unknown as Octokit
  })

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true })
  })

  const run = async (dryRun: boolean): Promise<Record<string, BugResult>> => {
    const results = await applyScores(
      { comments, fields },
      {
        logDir: dir,
        dryRun,
        marker: MARKER,
        agent: 'Claude Code',
        runUrl: 'https://run',
        date: '2026-11-20',
        warn: jest.fn(),
      },
    )
    return Object.fromEntries(results.map((result) => [result.ref, result]))
  }

  it('stores the comment and sends nothing on a dry run', async () => {
    const results = await run(true)
    expect(results['Jahia/example#1']?.outcome).toBe('scored')
    expect(results['Jahia/example#1']?.value).toBe(55)
    expect(results['Jahia/example#2']?.outcome).toBe('security')
    expect(results['Jahia/example#3']?.outcome).toBe('skipped')
    expect(existsSync(join(dir, 'comments', 'Jahia-example-1.comment.md'))).toBe(true)
    expect(existsSync(join(dir, 'comments', 'Jahia-example-2.comment.md'))).toBe(false)
    expect(sequence).toEqual([])
  })

  it('edits the comment then sets the field in write mode', async () => {
    const results = await run(false)
    expect(results['Jahia/example#1']?.written).toBe(true)
    expect(results['Jahia/example#1']?.comment_action).toBe('edited')
    // The bugs go in order, so the first three calls are those of bug 1.
    const first = sequence.slice(0, 3)
    expect(first[0]?.route).toBe('GET /repos/{owner}/{repo}/issues/{issue_number}/comments')
    expect(first[1]?.route).toBe('PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}')
    expect(first[1]?.params.comment_id).toBe(7)
    expect(String(first[1]?.params.body)).toMatch(new RegExp(`^${MARKER}`))
    expect(first[2]?.route).toBe(
      'field POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
    )
    expect(first[2]?.params.issue_number).toBe(1)
    expect(first[2]?.params.issue_field_values).toEqual([{ field_id: FIELD_ID, value: 55 }])
  })

  it('posts a new comment on a bug with no earlier score comment', async () => {
    existingComments = []
    const results = await run(false)
    expect(results['Jahia/example#1']?.comment_action).toBe('posted')
    const posts = sequence.filter(
      (call) => call.route === 'POST /repos/{owner}/{repo}/issues/{issue_number}/comments',
    )
    expect(posts).toHaveLength(1)
    expect(posts[0]?.params.issue_number).toBe(1)
  })

  it('gives a security bug minus one and no comment in write mode', async () => {
    await run(false)
    const security = sequence.filter((call) => call.params.issue_number === 2)
    expect(security).toHaveLength(1)
    expect(security[0]?.route).toBe(
      'field POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
    )
    expect(security[0]?.params.issue_field_values).toEqual([{ field_id: FIELD_ID, value: -1 }])
  })

  it('records a failed write and keeps processing the next bug', async () => {
    fieldsReject = true
    const results = await run(false)
    expect(results['Jahia/example#1']?.outcome).toBe('write failed')
    expect(results['Jahia/example#1']?.reason).toContain('field write refused')
    expect(results['Jahia/example#1']?.written).toBeUndefined()
    expect(results['Jahia/example#2']?.outcome).toBe('write failed')
    expect(results['Jahia/example#3']?.outcome).toBe('skipped')
  })

  it('sends nothing for a bug with no factors in write mode', async () => {
    const results = await run(false)
    expect(results['Jahia/example#3']?.written).toBeUndefined()
    expect(sequence.filter((call) => call.params.issue_number === 3)).toEqual([])
  })
})

describe('renderScoreSummary', () => {
  const results: BugResult[] = [
    {
      ref: 'Jahia/example#1',
      key: 'k1',
      url: 'https://u/1',
      outcome: 'scored',
      value: 155,
      p1: true,
      impact: 'data',
      reach: 'high',
      written: true,
    },
    {
      ref: 'Jahia/example#2',
      key: 'k2',
      url: 'https://u/2',
      outcome: 'security',
      value: -1,
      written: true,
    },
    {
      ref: 'Jahia/example#3',
      key: 'k3',
      url: 'https://u/3',
      outcome: 'skipped',
      reason: 'no factors (Error)',
    },
  ]

  it('renders one row per bug with the written suffix', () => {
    const table = renderScoreSummary(results, true)
    expect(table).toContain('### PM scores (written)')
    expect(table).toContain(
      '| [Jahia/example#1](https://u/1) | 155 | P1 | data / high | scored, written |',
    )
    expect(table).toContain('| [Jahia/example#2](https://u/2) | -1 |  |  | security, written |')
    expect(table).toContain(
      '| [Jahia/example#3](https://u/3) |  |  | no factors (Error) | skipped |',
    )
  })

  it('names the dry run in the heading', () => {
    expect(renderScoreSummary([], false)).toContain('### PM scores (dry run, nothing written)')
  })
})

describe('runFailure', () => {
  const written: BugResult = {
    ref: 'r',
    key: 'k',
    url: 'u',
    outcome: 'security',
    value: -1,
    written: true,
  }
  const skipped: BugResult = {
    ref: 'r',
    key: 'k',
    url: 'u',
    outcome: 'skipped',
    reason: 'no factors',
  }

  it('fails a write run in which nothing was written', () => {
    expect(runFailure([skipped], false)).toContain('no PM Score field was written')
    expect(runFailure([{ ...skipped, outcome: 'write failed' }], false)).toContain(
      'no PM Score field was written',
    )
  })

  it('passes a dry run, an empty selection and a run with one write', () => {
    expect(runFailure([skipped], true)).toBeNull()
    expect(runFailure([], false)).toBeNull()
    expect(runFailure([skipped, written], false)).toBeNull()
  })
})
