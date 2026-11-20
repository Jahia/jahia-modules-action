import type { Bug, Octokit } from '../types'

interface IssueComment {
  id: number
  body?: string | null
}

const LIST = 'GET /repos/{owner}/{repo}/issues/{issue_number}/comments'

// Edit the score comment of the bug when there is one, or post a new one. The pages are walked
// from the newest, so the read stops at the run's own last comment, not the whole history.
export const upsertComment = async (
  octokit: Octokit,
  bug: Bug,
  body: string,
  marker: string,
): Promise<'posted' | 'edited'> => {
  const [owner = '', repo = ''] = bug.repository.split('/')
  const base = { owner, repo, issue_number: bug.number, per_page: 100 }
  const first = await octokit.request(LIST, { ...base, page: 1 })
  const lastPage = Number(/[?&]page=(\d+)>; rel="last"/.exec(first.headers.link ?? '')?.[1] ?? '1')
  for (let page = lastPage; page >= 1; page -= 1) {
    const comments = (
      page === 1 ? first.data : (await octokit.request(LIST, { ...base, page })).data
    ) as IssueComment[]
    const mine = [...comments].reverse().find((comment) => (comment.body ?? '').startsWith(marker))
    if (mine) {
      await octokit.request('PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}', {
        owner,
        repo,
        comment_id: mine.id,
        body,
      })
      return 'edited'
    }
  }
  await octokit.request('POST /repos/{owner}/{repo}/issues/{issue_number}/comments', {
    owner,
    repo,
    issue_number: bug.number,
    body,
  })
  return 'posted'
}
