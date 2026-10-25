// An issue nobody owns gains the agent as its assignee the moment a session starts on it —
// deterministic, so it never depends on the agent remembering. An issue someone already
// owns is left alone here: whether the AGENT also belongs on it depends on what the session
// actually did (an implementation or a testing job — not a review, a spec or an answer),
// which only the session knows, so that call is the agent's own `assign`, as the cortex
// jahia-issue-agent skill states it.
export const selfAssignWhenUnassigned = async ({ github, owner, repo, issueNumber, agentLogin }) => {
  const { data: issue } = await github.rest.issues.get({ owner, repo, issue_number: issueNumber })
  if ((issue.assignees ?? []).length > 0) return false
  await github.rest.issues.addAssignees({
    owner,
    repo,
    issue_number: issueNumber,
    assignees: [agentLogin],
  })
  return true
}
