import type { Bug, Octokit } from '../types'

// The write the selection reads back: a value in the field means "scored".
export const setField = async (octokit: Octokit, bug: Bug, value: number): Promise<void> => {
  const [owner = '', repo = ''] = bug.repository.split('/')
  await octokit.request('POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values', {
    owner,
    repo,
    issue_number: bug.number,
    issue_field_values: [{ field_id: bug.field_id, value }],
  })
}
