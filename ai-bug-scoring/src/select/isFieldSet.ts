import type { Octokit } from '../types'

// An empty field means "not scored yet": an unset field is absent from the values array.
export const isFieldSet = async (
  octokit: Octokit,
  owner: string,
  repo: string,
  issueNumber: number,
  fieldId: number,
): Promise<boolean> => {
  const values = await octokit.paginate<{ issue_field_id: number }>(
    'GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
    { owner, repo, issue_number: issueNumber, per_page: 100 },
  )
  return values.some((value) => value.issue_field_id === fieldId)
}
