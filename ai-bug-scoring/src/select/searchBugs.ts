import type { Octokit } from '../types'

export interface FoundIssue {
  number: number
  html_url: string
  repository_url: string
  pull_request?: unknown
}

export interface SearchPage {
  data: FoundIssue[]
}

// Most recent first, so a new bug is scored while its ticket is fresh. The caller stops the page
// iterator early, so only the pages it needs count against the strict search rate limit.
export const searchBugs = (
  octokit: Octokit,
  searchScope: string,
): { query: string; pages: AsyncIterableIterator<SearchPage> } => {
  const query = `${searchScope} is:issue is:open type:Bug archived:false`
  // advanced_search is not in the typed route parameters yet, hence the cast.
  const parameters = {
    q: query,
    advanced_search: 'true',
    sort: 'created',
    order: 'desc',
    per_page: 100,
  }
  const pages = octokit.paginate.iterator(
    'GET /search/issues',
    parameters as never,
  ) as AsyncIterableIterator<SearchPage>
  return { query, pages }
}
