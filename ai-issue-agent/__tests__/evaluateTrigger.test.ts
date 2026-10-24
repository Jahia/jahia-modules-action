import { evaluateTrigger } from '../src/guard/evaluateTrigger'

const agentLogin = 'jahia-ai'

describe('evaluateTrigger', () => {
  it('qualifies a fresh comment mentioning the agent, carrying the instruction and the comment id', () => {
    const result = evaluateTrigger({
      eventName: 'issue_comment',
      payload: {
        action: 'created',
        issue: {},
        comment: {
          id: 77,
          body: '@jahia-ai please reproduce this',
          user: { login: 'a-developer' },
        },
      },
      agentLogin,
    })
    expect(result.qualifies).toBe(true)
    expect(result.trigger).toBe('mentioned')
    expect(result.instruction).toBe('@jahia-ai please reproduce this')
    expect(result.commentId).toBe(77)
  })

  it.each([
    [
      'an assignment to the agent (assignment no longer triggers a session)',
      { eventName: 'issues', payload: { action: 'assigned' } },
    ],
    [
      'a mention of a longer login sharing the prefix',
      {
        eventName: 'issue_comment',
        payload: {
          action: 'created',
          issue: {},
          comment: { body: 'ping @jahia-ai-foo', user: { login: 'a-developer' } },
        },
      },
    ],
    [
      'a comment without any mention',
      {
        eventName: 'issue_comment',
        payload: {
          action: 'created',
          issue: {},
          comment: { body: 'no agent here', user: { login: 'a-developer' } },
        },
      },
    ],
    [
      'a mention inside a pull request comment',
      {
        eventName: 'issue_comment',
        payload: {
          action: 'created',
          issue: { pull_request: { url: 'https://example.com' } },
          comment: { body: '@jahia-ai hello', user: { login: 'a-developer' } },
        },
      },
    ],
    [
      "the agent's own comment",
      {
        eventName: 'issue_comment',
        payload: {
          action: 'created',
          issue: {},
          comment: { body: '@jahia-ai status', user: { login: 'jahia-ai' } },
        },
      },
    ],
    [
      'a bot comment',
      {
        eventName: 'issue_comment',
        payload: {
          action: 'created',
          issue: {},
          comment: { body: '@jahia-ai status', user: { login: 'jahia-ci' } },
        },
      },
    ],
    [
      'an edited comment',
      {
        eventName: 'issue_comment',
        payload: {
          action: 'edited',
          issue: {},
          comment: { body: '@jahia-ai hello', user: { login: 'a-developer' } },
        },
      },
    ],
    ['an unrelated event', { eventName: 'label', payload: { action: 'created' } }],
  ])('does not qualify %s', (_name, event) => {
    const result = evaluateTrigger({ ...event, agentLogin })
    expect(result.qualifies).toBe(false)
    expect(result.reason).toBeTruthy()
  })
})
