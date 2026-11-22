import type { getOctokit } from '@actions/github'

export type Octokit = ReturnType<typeof getOctokit>

// One selected bug, as the select-bugs action emits it and every later step reads it.
export interface Bug {
  key: string
  repository: string
  number: number
  url: string
  field_id: number
}

export interface TicketComment {
  by: string | null
  at: string
  body: string
}

// One fetched ticket, cut at the sizes the rubric was calibrated on.
export interface Ticket {
  ref: string
  url: string
  title: string
  type: string | null
  visibility: string
  labels: string[]
  created: string
  body: string
  comments_total: number
  comments: TicketComment[]
}

// The factors the agent records. The keys are a contract between the rubric of the cortex
// jahia-pm-bug-scoring skill and the scoring tables: renaming one is a cross-repo change.
export interface Factors {
  ref: string
  security: boolean
  impact: string
  feature: string
  reach: string
  workaround: string
  regression: boolean
  clear: boolean
  cloud: boolean
  older_version_only: boolean
  customers: number
  confidence: string
  why: string
}

export interface ScoreRow {
  name: string
  text: string
  points: number
}

// The outcome of one bug, written to results.json and the job summary.
export interface BugResult {
  ref: string
  key: string
  url: string
  outcome: 'scored' | 'security' | 'skipped' | 'write failed'
  reason?: string
  value?: number
  points?: number
  impact?: string
  reach?: string
  customers?: number
  confidence?: string
  comment?: string
  comment_action?: 'posted' | 'edited'
  written?: boolean
}
