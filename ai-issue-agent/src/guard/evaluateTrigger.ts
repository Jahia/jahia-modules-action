import type { TriggerKind } from '../state/types'
import { escapeRegex } from './escapeRegex'

export interface TriggerEvaluation {
  qualifies: boolean
  trigger?: TriggerKind
  instruction?: string
  commentId?: number
  reason?: string
}

export interface TriggerEvent {
  eventName: string
  payload: {
    action?: string
    comment?: { id?: number; body?: string; user?: { login?: string } }
    issue?: { pull_request?: unknown }
  }
  agentLogin: string
}

// The authoritative trigger filter: ONLY a fresh issue comment mentioning the agent
// qualifies — assignment (or any other issue event) never starts a session. The
// workflow-level `if` is only a cheap pre-filter: it cannot match a mention on a login
// boundary, and it cannot see that an issue_comment event actually belongs to a pull
// request.
export const evaluateTrigger = ({
  eventName,
  payload,
  agentLogin,
}: TriggerEvent): TriggerEvaluation => {
  const agent = agentLogin.toLowerCase()
  if (eventName === 'issue_comment') {
    if (payload.action !== 'created') {
      return {
        qualifies: false,
        reason: `issue_comment action '${payload.action ?? 'unknown'}' is not 'created'`,
      }
    }
    if (payload.issue?.pull_request !== undefined) {
      return { qualifies: false, reason: 'the comment is on a pull request, not an issue' }
    }
    const author = (payload.comment?.user?.login ?? '').toLowerCase()
    if (author === agent || author === 'jahia-ci') {
      return { qualifies: false, reason: `comment author '${author}' is the agent itself or a bot` }
    }
    const body = payload.comment?.body ?? ''
    // (?![A-Za-z0-9-]) is a login boundary, not \b: logins may contain hyphens, so
    // "@jahia-ai-foo" must NOT count as a mention of "jahia-ai".
    const mention = new RegExp(`@${escapeRegex(agentLogin)}(?![A-Za-z0-9-])`, 'i')
    if (!mention.test(body)) {
      return { qualifies: false, reason: `the comment does not mention @${agentLogin}` }
    }
    return {
      qualifies: true,
      trigger: 'mentioned',
      instruction: body,
      commentId: payload.comment?.id,
    }
  }
  return { qualifies: false, reason: `event '${eventName}' never starts an agent` }
}
