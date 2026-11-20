import type { Bug, Ticket } from '../types'
import type { RepositoryNode } from './fetchTicket'

const BODY_LIMIT = 7000
const COMMENT_LIMIT = 1500
const COMMENT_COUNT = 15

// The body and the comments are cut at the sizes the rubric was calibrated on, and the score
// comment (opened by the marker) is left out of the text the agent reads.
export const toTicket = (bug: Bug, repo: RepositoryNode, marker: string): Ticket => {
  const issue = repo.issue
  if (!issue) throw new Error('issue not found')
  const comments = issue.comments.nodes.filter((comment) => !(comment.body ?? '').includes(marker))
  return {
    ref: `${bug.repository}#${String(bug.number)}`,
    url: issue.url,
    title: issue.title,
    type: issue.issueType?.name ?? null,
    visibility: repo.visibility,
    labels: issue.labels.nodes.map((label) => label.name),
    created: issue.createdAt.slice(0, 10),
    body: (issue.body ?? '').slice(0, BODY_LIMIT),
    comments_total: issue.comments.totalCount,
    comments: comments.slice(-COMMENT_COUNT).map((comment) => ({
      by: comment.author?.login ?? null,
      at: comment.createdAt.slice(0, 10),
      body: (comment.body ?? '').slice(0, COMMENT_LIMIT),
    })),
  }
}
