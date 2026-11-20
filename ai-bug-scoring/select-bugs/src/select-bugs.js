// Selects the bugs that wait for a PM score: on each board, the open issues that match the board's
// filter and whose score field is still empty.
//
// The rule is deterministic: an empty field means "not scored yet". The scoring job writes the
// field, or -1 for a security bug, so a bug is read once. A person who empties the field asks for
// a new score.
const ITEMS = `
query($org: String!, $number: Int!, $filter: String!, $after: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      title
      fields(first: 100) { nodes { ... on ProjectV2FieldCommon { id name dataType } } }
      items(first: 100, after: $after, query: $filter) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content { __typename ... on Issue { number url state repository { nameWithOwner } } }
        }
      }
    }
  }
}`

async function readBoard(github, core, org, {board, filter, field}) {
  const query = `${filter} no:"${field}"`
  const items = []
  let after = null
  let project = null
  do {
    const data = await github.graphql(ITEMS, {org, number: board, filter: query, after})
    project = data.organization.projectV2
    items.push(...project.items.nodes)
    after = project.items.pageInfo.hasNextPage ? project.items.pageInfo.endCursor : null
  } while (after)

  const scoreField = project.fields.nodes.find(f => f && f.name === field)
  if (!scoreField || scoreField.dataType !== 'NUMBER') {
    throw new Error(`Board ${board} (${project.title}) has no number field named "${field}"`)
  }
  const issues = items.filter(i => i.content?.__typename === 'Issue' && i.content.state === 'OPEN')
  core.info(`Board ${board} (${project.title}): ${issues.length} open issue(s) match: ${query}`)
  return issues.map(i => ({
    repository: i.content.repository.nameWithOwner,
    number: i.content.number,
    url: i.content.url,
    target: {board, project_id: project.id, item_id: i.id, field_id: scoreField.id, field},
  }))
}

module.exports = async ({github, core}, {org, boards, maxBugs}) => {
  // One entry per issue: a bug can wait on both boards, and one score fills both fields.
  const byIssue = new Map()
  for (const board of boards) {
    for (const found of await readBoard(github, core, org, board)) {
      const key = `${found.repository.replace('/', '-')}-${found.number}`
      if (!byIssue.has(key)) {
        byIssue.set(key, {key, repository: found.repository, number: found.number, url: found.url, targets: []})
      }
      byIssue.get(key).targets.push(found.target)
    }
  }

  const all = [...byIssue.values()]
    .sort((a, b) => a.repository.localeCompare(b.repository) || a.number - b.number)
  const selected = all.slice(0, maxBugs)
  core.info(`${selected.length} of ${all.length} bug(s) selected (at most ${maxBugs} per run):`)
  for (const bug of selected) {
    core.info(`  - ${bug.repository}#${bug.number} → ${bug.targets.map(t => t.field).join(', ')}`)
  }

  await core.summary
    .addHeading('Bug selection', 3)
    .addRaw(`\n${selected.length} of ${all.length} bug(s) wait for a PM score; at most ${maxBugs} per run.\n\n`)
    .addTable([
      [{data: 'Bug', header: true}, {data: 'Fields to fill', header: true}],
      ...selected.map(b => [`${b.repository}#${b.number}`, b.targets.map(t => t.field).join(', ')]),
    ])
    .write()

  return selected
}
