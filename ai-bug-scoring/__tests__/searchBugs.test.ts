import { searchBugs } from '../src/select/searchBugs'
import type { Octokit } from '../src/types'

describe('searchBugs', () => {
  it('asks for the newest bugs first and returns the page iterator', async () => {
    const captured: { route?: string; params?: Record<string, unknown> } = {}
    const octokit = {
      paginate: {
        iterator: jest.fn((route: string, params: Record<string, unknown>) => {
          captured.route = route
          captured.params = params
          return (async function* () {
            yield await Promise.resolve({ data: [{ number: 1 }] })
          })()
        }),
      },
    } as unknown as Octokit

    const { query, pages } = searchBugs(octokit, 'org:Jahia')
    expect(query).toBe('org:Jahia is:issue is:open type:Bug archived:false')
    expect(captured.route).toBe('GET /search/issues')
    expect(captured.params).toEqual({
      q: 'org:Jahia is:issue is:open type:Bug archived:false',
      advanced_search: 'true',
      sort: 'created',
      order: 'desc',
      per_page: 100,
    })
    const first = await pages.next()
    expect(first.value).toEqual({ data: [{ number: 1 }] })
  })
})
