import type { GitHub } from '@actions/github/lib/utils'
import { STATUS_MARKER } from './markers'

type Octokit = InstanceType<typeof GitHub>

export interface StatusComment {
  id: number
  body: string
}

// The overall-status comment is identified by its hidden marker, never by position:
// humans may have commented before the agent's first touch.
export const findStatusComment = async (
  octokit: Octokit,
  params: { owner: string; repo: string; issueNumber: number },
): Promise<StatusComment | null> => {
  const comments = await octokit.paginate(octokit.rest.issues.listComments, {
    owner: params.owner,
    repo: params.repo,
    issue_number: params.issueNumber,
    per_page: 100,
  })
  const found = comments.find((comment) => (comment.body ?? '').includes(STATUS_MARKER))
  return found ? { id: found.id, body: found.body ?? '' } : null
}
