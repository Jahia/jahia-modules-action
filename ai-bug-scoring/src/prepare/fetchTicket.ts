import type { Octokit } from '../types'

export interface IssueNode {
  title: string
  url: string
  body: string | null
  createdAt: string
  issueType: { name: string } | null
  labels: { nodes: { name: string }[] }
  comments: {
    totalCount: number
    nodes: { author: { login: string } | null; createdAt: string; body: string | null }[]
  }
}

export interface RepositoryNode {
  visibility: string
  issue: IssueNode | null
}

const QUERY = `
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    visibility
    issue(number: $number) {
      title url body createdAt
      issueType { name }
      labels(first: 50) { nodes { name } }
      comments(last: 15) { totalCount nodes { author { login } createdAt body } }
    }
  }
}`

// One GraphQL read per bug: the text the agent judges, and the labels the scoring gates on.
export const fetchTicket = async (
  octokit: Octokit,
  repository: string,
  number: number,
): Promise<RepositoryNode> => {
  const [owner = '', name = ''] = repository.split('/')
  const data = await octokit.graphql<{ repository: RepositoryNode }>(QUERY, { owner, name, number })
  return data.repository
}
