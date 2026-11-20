import type { Bug, Octokit } from '../types'

// Edit the score comment of the bug when there is one, or post a new one.
export const upsertComment = async (
  octokit: Octokit,
  bug: Bug,
  body: string,
  marker: string,
): Promise<'posted' | 'edited'> => {
  const [owner = '', repo = ''] = bug.repository.split('/')
  const comments = (await octokit.paginate(
    'GET /repos/{owner}/{repo}/issues/{issue_number}/comments',
    { owner, repo, issue_number: bug.number, per_page: 100 },
  )) as { id: number; body?: string | null }[]
  const mine = comments.filter((comment) => (comment.body ?? '').startsWith(marker))
  const last = mine[mine.length - 1]
  if (last) {
    await octokit.request('PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}', {
      owner,
      repo,
      comment_id: last.id,
      body,
    })
    return 'edited'
  }
  await octokit.request('POST /repos/{owner}/{repo}/issues/{issue_number}/comments', {
    owner,
    repo,
    issue_number: bug.number,
    body,
  })
  return 'posted'
}
