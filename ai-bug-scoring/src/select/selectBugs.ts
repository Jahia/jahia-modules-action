import type { Bug, Octokit } from '../types'
import { findScoreField } from './findScoreField'
import { isFieldSet } from './isFieldSet'
import { searchBugs } from './searchBugs'

export interface Selection {
  query: string
  seen: number
  read: number
  selected: Bug[]
}

// Deterministic: keeps the open issues of type Bug whose score field is empty, most recent first,
// and stops at maxBugs. A person who empties the field asks for a new score.
export const selectBugs = async (
  octokit: Octokit,
  {
    org,
    searchScope,
    field,
    maxBugs,
  }: { org: string; searchScope: string; field: string; maxBugs: number },
): Promise<Selection> => {
  const scoreField = await findScoreField(octokit, org, field)
  const { query, pages } = searchBugs(octokit, searchScope)
  const selected: Bug[] = []
  let seen = 0
  let read = 0
  outer: for await (const page of pages) {
    for (const issue of page.data) {
      seen += 1
      if (issue.pull_request) continue
      const [owner = '', repo = ''] = issue.repository_url.split('/').slice(-2)
      read += 1
      if (await isFieldSet(octokit, owner, repo, issue.number, scoreField.id)) continue
      selected.push({
        key: `${owner}-${repo}-${String(issue.number)}`,
        repository: `${owner}/${repo}`,
        number: issue.number,
        url: issue.html_url,
        field_id: scoreField.id,
      })
      if (selected.length >= maxBugs) break outer
    }
  }
  // Deterministic processing order for the agent job.
  selected.sort((a, b) => a.repository.localeCompare(b.repository) || a.number - b.number)
  return { query, seen, read, selected }
}
