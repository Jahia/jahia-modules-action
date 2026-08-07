// Selects open incident issues — across every repository the search scope covers —
// whose latest failure event has not yet been handled by the triage agent (no marker
// comment posted after it).
//
// The rule is deliberately deterministic: one agent action per failure event.
// A triage comment (identified by the hidden marker) posted AFTER the latest
// failure event marks that failure as handled; a NEW failure comment arriving
// later re-arms the issue for exactly one more triage pass.
module.exports = async ({github, core}, {searchScope, label, marker}) => {
  const FAILURE_SIGNATURE = /Source URL:|### Failure Details/
  const query = `${searchScope} is:issue is:open label:"${label}"`

  const found = await github.paginate(github.rest.search.issuesAndPullRequests, {
    q: query, advanced_search: 'true', per_page: 100,
  })
  core.info(`${found.length} open '${label}' issue(s) found by search: ${query}`)

  const eligible = []
  for (const issue of found) {
    if (issue.pull_request) continue
    const [owner, repo] = issue.repository_url.split('/').slice(-2)

    const comments = await github.paginate(github.rest.issues.listComments, {
      owner, repo, issue_number: issue.number, per_page: 100,
    })

    // Failure events: the issue body plus every comment matching the incident template.
    const failureEvents = [
      {body: issue.body ?? '', created_at: issue.created_at},
      ...comments,
    ].filter(e => FAILURE_SIGNATURE.test(e.body ?? ''))
    if (failureEvents.length === 0) {
      core.info(`${owner}/${repo}#${issue.number}: no failure-details event found, skipping`)
      continue
    }

    const latestFailure = failureEvents.reduce((a, b) =>
      new Date(a.created_at) > new Date(b.created_at) ? a : b)

    const handled = comments.some(c =>
      (c.body ?? '').includes(marker) &&
      new Date(c.created_at) > new Date(latestFailure.created_at))
    if (handled) {
      core.info(`${owner}/${repo}#${issue.number}: latest failure already triaged, skipping`)
      continue
    }

    const sourceRunUrl = (latestFailure.body.match(/Source URL:\*{0,2}\s*(\S+)/) ?? [])[1] ?? ''
    const vpnArtifactsUrl = (latestFailure.body.match(/https:\/\/qa\.jahia\.com\/artifacts-ci\/\S+/) ?? [])[0] ?? ''

    eligible.push({
      repository: `${owner}/${repo}`,
      number: issue.number,
      title: issue.title,
      html_url: issue.html_url,
      latest_failure_at: latestFailure.created_at,
      source_run_url: sourceRunUrl,
      vpn_artifacts_url: vpnArtifactsUrl,
    })
  }

  // Deterministic processing order for the agent job.
  eligible.sort((a, b) => a.repository.localeCompare(b.repository) || a.number - b.number)

  core.info(`${eligible.length}/${found.length} issue(s) eligible for triage`)

  // Observability: publish the exact selection to the job summary.
  await core.summary
    .addHeading('Incident issue selection', 3)
    .addRaw(`\nSearch: \`${query}\` — ${eligible.length} of ${found.length} issue(s) eligible for triage.\n\n`)
    .addCodeBlock(JSON.stringify(eligible, null, 2), 'json')
    .write()

  return eligible
}
