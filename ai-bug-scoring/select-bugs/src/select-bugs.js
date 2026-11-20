// Selects the bugs that wait for a PM score: the open issues of type Bug, across every repository
// the search scope covers, whose PM Score issue field is empty.
//
// The rule is deterministic: an empty field means "not scored yet". The scoring job writes the
// field, or -1 for a security bug, so a bug is read once. A person who empties the field asks for
// a new score.
module.exports = async ({github, core}, {org, searchScope, field, maxBugs}) => {
  const fields = await github.paginate('GET /orgs/{org}/issue-fields', {org, per_page: 100})
  const scoreField = fields.find(f => f.name === field)
  if (!scoreField || scoreField.data_type !== 'number') {
    throw new Error(`Organization ${org} has no number issue field named "${field}"`)
  }

  // The search cannot filter on an issue field, so the job reads the field of each found issue
  // and stops once maxBugs bugs with an empty field are collected. Oldest first: the search
  // returns at most 1000 issues, so the cap drops the newest bugs, which wait until the backlog
  // in front of them is scored.
  const query = `${searchScope} is:issue is:open type:Bug archived:false`
  const found = await github.paginate(github.rest.search.issuesAndPullRequests, {
    q: query, advanced_search: 'true', sort: 'created', order: 'asc', per_page: 100,
  })
  core.info(`${found.length} open bug(s) found by search: ${query}`)

  const selected = []
  let read = 0
  for (const issue of found) {
    if (issue.pull_request) continue
    if (selected.length >= maxBugs) break
    const [owner, repo] = issue.repository_url.split('/').slice(-2)
    const values = await github.paginate(
      'GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values',
      {owner, repo, issue_number: issue.number, per_page: 100})
    read += 1
    if (values.some(v => v.issue_field_id === scoreField.id)) continue
    selected.push({
      key: `${owner}-${repo}-${issue.number}`,
      repository: `${owner}/${repo}`,
      number: issue.number,
      url: issue.html_url,
      field_id: scoreField.id,
    })
  }

  // Deterministic processing order for the agent job.
  selected.sort((a, b) => a.repository.localeCompare(b.repository) || a.number - b.number)
  core.info(`${selected.length} bug(s) selected (at most ${maxBugs} per run, ${read} field read(s)):`)
  for (const bug of selected) {
    core.info(`  - ${bug.repository}#${bug.number}`)
  }

  await core.summary
    .addHeading('Bug selection', 3)
    .addRaw(`\nSearch: \`${query}\` — ${found.length} open bug(s); ${selected.length} selected ` +
            `whose "${field}" field is empty (at most ${maxBugs} per run).\n\n`)
    .addTable([
      [{data: 'Bug', header: true}],
      ...selected.map(b => [`${b.repository}#${b.number}`]),
    ])
    .write()

  return selected
}
