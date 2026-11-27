import { buildContext, readEvent } from '../src/triage/context'

const event = (overrides: Record<string, unknown> = {}): Record<string, unknown> => ({
  issue: {
    number: 721,
    title: 'test: a throwaway thread',
    body: 'The description.',
    labels: [{ name: 'bug' }, 'plain', { name: '' }, { color: 'red' }],
  },
  comment: { id: 99, body: '@jahia-ai please do it', user: { login: 'someone' } },
  repository: { full_name: 'Jahia/sandbox', default_branch: 'main' },
  ...overrides,
})

describe('readEvent', () => {
  it('reads the thread, the comment and the repository', () => {
    expect(readEvent(event(), 'issue')).toEqual({
      origin: { repo: 'Jahia/sandbox', number: 721, kind: 'issue', comment_id: 99 },
      title: 'test: a throwaway thread',
      labels: ['bug', 'plain'],
      body: 'The description.',
      request: '@jahia-ai please do it',
      author: 'someone',
      defaultBranch: 'main',
    })
  })

  it('takes the kind from the guard and not from the event', () => {
    expect(readEvent(event(), 'pull_request').origin.kind).toBe('pull_request')
  })

  it('takes the default branch of the repository, and main when it is missing', () => {
    expect(
      readEvent(event({ repository: { full_name: 'Jahia/x', default_branch: 'master' } }), 'issue')
        .defaultBranch,
    ).toBe('master')
    expect(readEvent(event({ repository: { full_name: 'Jahia/x' } }), 'issue').defaultBranch).toBe(
      'main',
    )
  })

  it('writes a question mark for an author that the event does not name', () => {
    expect(readEvent(event({ comment: { id: 5, body: 'x' } }), 'issue').author).toBe('?')
  })

  it('tolerates an issue with no body and no labels', () => {
    const parsed = readEvent(event({ issue: { number: 3, title: 't', body: null } }), 'issue')
    expect(parsed.body).toBe('')
    expect(parsed.labels).toEqual([])
  })

  it.each([
    ['a string', 'event'],
    ['an event without a comment', { issue: { number: 1 }, repository: { full_name: 'a/b' } }],
    ['an event without an issue', { comment: { id: 1 }, repository: { full_name: 'a/b' } }],
    ['an event without a repository', { issue: { number: 1 }, comment: { id: 1 } }],
    ['a repository with no name', event({ repository: { default_branch: 'main' } })],
    ['an issue number of zero', event({ issue: { number: 0 } })],
    ['a comment id that is a string', event({ comment: { id: '99' } })],
  ])('refuses %s', (_name, value) => {
    expect(() => readEvent(value, 'issue')).toThrow()
  })
})

describe('buildContext', () => {
  const parsed = readEvent(event(), 'issue')

  it('builds the context of the schema', () => {
    expect(buildContext(parsed, 5400)).toEqual({
      origin: parsed.origin,
      title: 'test: a throwaway thread',
      labels: ['bug', 'plain'],
      body: 'The description.',
      request: '@jahia-ai please do it',
      remaining_budget_seconds: 5400,
    })
  })

  it('cuts a long description and a long request to the limits of the schema', () => {
    const long = { ...parsed, body: 'b'.repeat(9000), request: 'r'.repeat(9000) }
    const context = buildContext(long, 100)
    expect(context.body).toHaveLength(4000)
    expect(context.request).toHaveLength(2000)
  })

  it('leaves out a remaining budget that is unknown or negative', () => {
    expect(buildContext(parsed, Number.NaN)).not.toHaveProperty('remaining_budget_seconds')
    expect(buildContext(parsed, -1)).not.toHaveProperty('remaining_budget_seconds')
  })

  it('rounds the remaining budget down, and accepts zero', () => {
    expect(buildContext(parsed, 12.9).remaining_budget_seconds).toBe(12)
    expect(buildContext(parsed, 0).remaining_budget_seconds).toBe(0)
  })
})
