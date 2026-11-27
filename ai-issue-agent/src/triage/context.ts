import type { Origin } from './plan'

// What the triage reads about a request: the thread and the comment that mentions the agent. The
// event of the workflow already holds both, so the dispatch makes no API call to build the context.

export interface ParsedEvent {
  origin: Origin
  title: string
  labels: string[]
  body: string
  // The whole comment that mentions the agent. The triage reads a cut of it, the session the whole.
  request: string
  author: string
  defaultBranch: string
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const text = (value: unknown): string => (typeof value === 'string' ? value : '')

const integer = (value: unknown, what: string): number => {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1) {
    throw new Error(`the event has no valid ${what}`)
  }
  return value
}

export const readEvent = (event: unknown, kind: 'issue' | 'pull_request'): ParsedEvent => {
  if (!isRecord(event)) throw new Error('the event is not an object')
  const { issue, comment, repository } = event
  if (!isRecord(issue) || !isRecord(comment) || !isRecord(repository)) {
    throw new Error('the event is not an issue comment event')
  }
  const repo = text(repository.full_name)
  if (repo === '') throw new Error('the event names no repository')
  const labels = Array.isArray(issue.labels)
    ? issue.labels
        .map((label): string => (isRecord(label) ? text(label.name) : text(label)))
        .filter((name) => name !== '')
    : []
  return {
    origin: {
      repo,
      number: integer(issue.number, 'issue number'),
      kind,
      comment_id: integer(comment.id, 'comment id'),
    },
    title: text(issue.title),
    labels,
    body: text(issue.body),
    request: text(comment.body),
    author: isRecord(comment.user) ? text(comment.user.login) || '?' : '?',
    defaultBranch: text(repository.default_branch) || 'main',
  }
}

// The limits of the schema of the context. The tool cuts a longer text too, and a cut here keeps a
// long thread from being refused for its length.
const MAX_BODY = 4000
const MAX_REQUEST = 2000

export interface TriageContext {
  origin: Origin
  title: string
  labels: string[]
  body: string
  request: string
  remaining_budget_seconds?: number
}

export const buildContext = (parsed: ParsedEvent, remainingSeconds: number): TriageContext => ({
  origin: parsed.origin,
  title: parsed.title,
  labels: parsed.labels,
  body: parsed.body.slice(0, MAX_BODY),
  request: parsed.request.slice(0, MAX_REQUEST),
  ...(Number.isFinite(remainingSeconds) && remainingSeconds >= 0
    ? { remaining_budget_seconds: Math.floor(remainingSeconds) }
    : {}),
})
