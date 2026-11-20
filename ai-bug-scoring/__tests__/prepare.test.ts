import { batchKeys } from '../src/prepare/batchKeys'
import { buildPrompt } from '../src/prepare/buildPrompt'
import type { RepositoryNode } from '../src/prepare/fetchTicket'
import { toTicket } from '../src/prepare/toTicket'
import { MARKER, bug } from './fixtures'

describe('batchKeys', () => {
  it('splits the keys into batches of the given size', () => {
    expect(batchKeys(['a', 'b', 'c', 'd', 'e'], 2)).toEqual([['a', 'b'], ['c', 'd'], ['e']])
  })

  it('treats a size below one as one', () => {
    expect(batchKeys(['a', 'b'], 0)).toEqual([['a'], ['b']])
  })

  it('returns no batch for no keys', () => {
    expect(batchKeys([], 10)).toEqual([])
  })
})

describe('buildPrompt', () => {
  it('substitutes every placeholder', () => {
    expect(
      buildPrompt('read __RUBRIC__ for __COUNT__ tickets', { RUBRIC: '/r.md', COUNT: '2' }),
    ).toBe('read /r.md for 2 tickets')
  })

  it('refuses a template with a placeholder left over', () => {
    expect(() => buildPrompt('read __RUBRIC__ and __TICKETS__', { RUBRIC: '/r.md' })).toThrow(
      'prompt template placeholder not replaced: __TICKETS__',
    )
  })
})

describe('toTicket', () => {
  const repo = (over: Partial<NonNullable<RepositoryNode['issue']>> = {}): RepositoryNode => ({
    visibility: 'PRIVATE',
    issue: {
      title: 'A bug',
      url: 'https://github.com/Jahia/example/issues/1',
      body: 'body text',
      createdAt: '2026-01-02T03:04:05Z',
      issueType: { name: 'Bug' },
      labels: { nodes: [{ name: 'customer' }] },
      comments: {
        totalCount: 2,
        nodes: [
          {
            author: { login: 'a-developer' },
            createdAt: '2026-01-03T00:00:00Z',
            body: 'a comment',
          },
          { author: null, createdAt: '2026-01-04T00:00:00Z', body: `${MARKER}\nan old score` },
        ],
      },
      ...over,
    },
  })

  it('maps the issue and leaves the score comment out', () => {
    const ticket = toTicket(bug(1), repo(), MARKER)
    expect(ticket.ref).toBe('Jahia/example#1')
    expect(ticket.type).toBe('Bug')
    expect(ticket.labels).toEqual(['customer'])
    expect(ticket.created).toBe('2026-01-02')
    expect(ticket.comments).toEqual([{ by: 'a-developer', at: '2026-01-03', body: 'a comment' }])
    expect(ticket.comments_total).toBe(2)
  })

  it('cuts the body at the calibrated size', () => {
    const ticket = toTicket(bug(1), repo({ body: 'x'.repeat(9000) }), MARKER)
    expect(ticket.body).toHaveLength(7000)
  })

  it('keeps the last 15 comments, each cut at 1500, and leaves the score comment out', () => {
    const nodes = Array.from({ length: 20 }, (_, index) => ({
      author: { login: `user-${String(index + 1)}` },
      createdAt: '2026-01-05T00:00:00Z',
      body: `comment ${String(index + 1)} ${'x'.repeat(2000)}`,
    }))
    nodes.push({
      author: { login: 'jahia-ai' },
      createdAt: '2026-01-06T00:00:00Z',
      body: `${MARKER}\nan old score`,
    })
    const ticket = toTicket(bug(1), repo({ comments: { totalCount: 21, nodes } }), MARKER)
    expect(ticket.comments).toHaveLength(15)
    expect(ticket.comments[0]?.by).toBe('user-6')
    expect(ticket.comments[14]?.by).toBe('user-20')
    for (const comment of ticket.comments) expect(comment.body.length).toBeLessThanOrEqual(1500)
    expect(ticket.comments.some((comment) => comment.body.includes(MARKER))).toBe(false)
  })

  it('refuses a repository with no such issue', () => {
    expect(() => toTicket(bug(1), { visibility: 'PRIVATE', issue: null }, MARKER)).toThrow(
      'issue not found',
    )
  })
})
