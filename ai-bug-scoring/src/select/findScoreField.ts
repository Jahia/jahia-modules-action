import type { Octokit } from '../types'

export interface IssueField {
  id: number
  name: string
  data_type: string
}

// The field is defined once on the organization, and its id is what the value endpoints take.
export const findScoreField = async (
  octokit: Octokit,
  org: string,
  field: string,
): Promise<IssueField> => {
  const fields = await octokit.paginate<IssueField>('GET /orgs/{org}/issue-fields', {
    org,
    per_page: 100,
  })
  const scoreField = fields.find((candidate) => candidate.name === field)
  if (scoreField?.data_type !== 'number') {
    throw new Error(`Organization ${org} has no number issue field named "${field}"`)
  }
  return scoreField
}
