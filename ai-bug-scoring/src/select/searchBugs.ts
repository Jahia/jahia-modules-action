import type { Octokit } from '../types'

export interface FoundIssue {
  number: number
  html_url: string
  repository_url: string
  pull_request?: unknown
}

// Most recent first, so a new bug is scored while its ticket is fresh; the oldest bugs wait
// until the backlog in front of them is scored, and the 1000-result cap of the search drops
// them first.
export const searchBugs = async (
  octokit: Octokit,
  searchScope: string,
): Promise<{ query: string; found: FoundIssue[] }> => {
  const query = `${searchScope} is:issue is:open type:Bug archived:false`
  // advanced_search is not in the typed route parameters yet, hence the cast.
  const parameters = {
    q: query,
    advanced_search: 'true',
    sort: 'created',
    order: 'desc',
    per_page: 100,
  }
  const found = await octokit.paginate<FoundIssue>('GET /search/issues', parameters as never)
  return { query, found }
}
