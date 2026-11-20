import type { Octokit } from '../types'

// The rubric lives in the jahia-pm-bug-scoring skill of Jahia/cortex — one home for the scoring
// judgment — and is fetched at the ref the caller pins.
export const fetchRubric = async (octokit: Octokit, ref: string): Promise<string> => {
  const response = await octokit.request('GET /repos/{owner}/{repo}/contents/{path}', {
    owner: 'Jahia',
    repo: 'cortex',
    path: '.claude/skills/jahia-pm-bug-scoring/assets/rubric.md',
    ref,
    headers: { accept: 'application/vnd.github.raw+json' },
  })
  return response.data as unknown as string
}
