import type { Bug, Octokit } from '../types'
import { findScoreField } from './findScoreField'
import { isFieldSet } from './isFieldSet'
import { searchBugs } from './searchBugs'

export interface Selection {
  query: string
  foundCount: number
  read: number
  field: string
  selected: Bug[]
}

// Deterministic: selects the open issues of type Bug whose score field is empty, and stops once
// maxBugs are collected. The search cannot filter on an issue field, so the field of each found
// issue is read, most recent first. The scoring job writes the field, or -1 for a security bug,
// so a bug is read once. A person who empties the field asks for a new score.
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
  const { query, found } = await searchBugs(octokit, searchScope)
  const selected: Bug[] = []
  let read = 0
  for (const issue of found) {
    if (issue.pull_request) continue
    if (selected.length >= maxBugs) break
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
  }
  // Deterministic processing order for the agent job.
  selected.sort((a, b) => a.repository.localeCompare(b.repository) || a.number - b.number)
  return { query, foundCount: found.length, read, field, selected }
}
