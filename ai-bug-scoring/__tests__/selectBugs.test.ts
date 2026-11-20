import { selectBugs } from '../src/select/selectBugs'
import type { Octokit } from '../src/types'
import { FIELD_ID } from './fixtures'

const issue = (repo: string, number: number): Record<string, unknown> => ({
  number,
  html_url: `https://github.com/Jahia/${repo}/issues/${String(number)}`,
  repository_url: `https://api.github.com/repos/Jahia/${repo}`,
})

const options = { org: 'Jahia', searchScope: 'org:Jahia', field: 'PM Score', maxBugs: 30 }

const fakeOctokit = (
  found: Record<string, unknown>[],
  valuesByIssue: Record<number, { issue_field_id: number }[]>,
  fields: Record<string, unknown>[] = [{ id: FIELD_ID, name: 'PM Score', data_type: 'number' }],
): { octokit: Octokit; paginate: jest.Mock } => {
  const paginate = jest.fn((route: string, params: Record<string, unknown>) => {
    if (route === 'GET /orgs/{org}/issue-fields') return Promise.resolve(fields)
    if (route === 'GET /search/issues') return Promise.resolve(found)
    return Promise.resolve(valuesByIssue[params.issue_number as number] ?? [])
  })
  return { octokit: { paginate } as unknown as Octokit, paginate }
}

describe('selectBugs', () => {
  it('keeps the bugs whose field is empty and sorts them by repository and number', async () => {
    const { octokit } = fakeOctokit([issue('zeta', 9), issue('alpha', 3), issue('alpha', 1)], {
      3: [{ issue_field_id: FIELD_ID }],
    })
    const selection = await selectBugs(octokit, options)
    expect(selection.selected.map((bug) => bug.key)).toEqual(['Jahia-alpha-1', 'Jahia-zeta-9'])
    expect(selection.selected[0]).toEqual({
      key: 'Jahia-alpha-1',
      repository: 'Jahia/alpha',
      number: 1,
      url: 'https://github.com/Jahia/alpha/issues/1',
      field_id: FIELD_ID,
    })
    expect(selection.foundCount).toBe(3)
    expect(selection.read).toBe(3)
  })

  it('ignores a value of another field', async () => {
    const { octokit } = fakeOctokit([issue('alpha', 1)], { 1: [{ issue_field_id: 999 }] })
    const selection = await selectBugs(octokit, options)
    expect(selection.selected).toHaveLength(1)
  })

  it('skips pull requests without reading their field', async () => {
    const { octokit, paginate } = fakeOctokit([{ ...issue('alpha', 1), pull_request: {} }], {})
    const selection = await selectBugs(octokit, options)
    expect(selection.selected).toEqual([])
    const valueReads = paginate.mock.calls.filter(
      (call: unknown[]) =>
        call[0] === 'GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
    )
    expect(valueReads).toHaveLength(0)
  })

  it('stops reading once maxBugs bugs are collected', async () => {
    const { octokit, paginate } = fakeOctokit(
      [issue('alpha', 1), issue('alpha', 2), issue('alpha', 3)],
      {},
    )
    const selection = await selectBugs(octokit, { ...options, maxBugs: 2 })
    expect(selection.selected).toHaveLength(2)
    const valueReads = paginate.mock.calls.filter(
      (call: unknown[]) =>
        call[0] === 'GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
    )
    expect(valueReads).toHaveLength(2)
  })

  it('refuses an organization with no number field of that name', async () => {
    const { octokit } = fakeOctokit([], {}, [{ id: 1, name: 'PM Score', data_type: 'text' }])
    await expect(selectBugs(octokit, options)).rejects.toThrow(
      'Organization Jahia has no number issue field named "PM Score"',
    )
  })
})
