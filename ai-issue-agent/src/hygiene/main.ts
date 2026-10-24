import * as core from '@actions/core'
import * as github from '@actions/github'
import { parseProjectUrl } from './parseProjectUrl'
import { pickOption } from './pickOption'

// project-hygiene entry point: an issue the agent session works on is always on the board,
// prioritized, truthfully statused, and owned by a squad. Idempotent by construction —
// addProjectV2ItemById returns the existing item, Priority/Status are set to the requested
// value every time, and Squad is only defaulted when unset. A missing field or option
// fails loud with what the board actually offers.

interface ProjectOption {
  id: string
  name: string
}

interface ProjectField {
  id: string
  name: string
  options?: ProjectOption[]
}

interface ProjectQuery {
  organization: { projectV2: { id: string; fields: { nodes: ProjectField[] } } }
}

interface AddItemMutation {
  addProjectV2ItemById: { item: { id: string } }
}

interface ItemValueQuery {
  node: { value?: { name?: string } | null } | null
}

const FIELD_STATUS = 'Status'
const FIELD_PRIORITY = 'Priority'
const FIELD_SQUAD = 'Squad'

const run = async (): Promise<void> => {
  const token = core.getInput('github_token', { required: true })
  const repository = core.getInput('repository') || (process.env.GITHUB_REPOSITORY ?? '')
  const issueNumber = Number(core.getInput('issue_number', { required: true }))
  const projectUrl = core.getInput('project_url') || 'https://github.com/orgs/Jahia/projects/50'
  const status = core.getInput('status')
  const priority = core.getInput('priority') || 'Now'
  const squadDefault = core.getInput('squad_default') || '🐐 GOAT'
  const [owner = '', repo = ''] = repository.split('/')
  const key = `${repository}#${String(issueNumber)}`
  const { org, number } = parseProjectUrl(projectUrl)

  const octokit = github.getOctokit(token)
  const issue = await octokit.rest.issues.get({ owner, repo, issue_number: issueNumber })
  const contentId = issue.data.node_id

  const project = await octokit.graphql<ProjectQuery>(
    `query ($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          id
          fields(first: 50) {
            nodes {
              ... on ProjectV2FieldCommon { id name }
              ... on ProjectV2SingleSelectField { id name options { id name } }
            }
          }
        }
      }
    }`,
    { org, number },
  )
  const projectId = project.organization.projectV2.id
  const fields = project.organization.projectV2.fields.nodes

  const added = await octokit.graphql<AddItemMutation>(
    `mutation ($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }`,
    { projectId, contentId },
  )
  const itemId = added.addProjectV2ItemById.item.id
  core.info(`${key}: on project ${org}/${String(number)} as item ${itemId}`)

  const setSingleSelect = async (fieldName: string, optionName: string): Promise<void> => {
    const field = fields.find((candidate) => candidate.name === fieldName)
    if (!field?.options) {
      throw new Error(
        `the project has no single-select field '${fieldName}' (fields: ${fields.map((candidate) => candidate.name).join(', ')})`,
      )
    }
    const optionId = pickOption(field.options, optionName)
    if (optionId === null) {
      throw new Error(
        `field '${fieldName}' has no option '${optionName}' (options: ${field.options.map((option) => option.name).join(', ')})`,
      )
    }
    await octokit.graphql(
      `mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
        updateProjectV2ItemFieldValue(
          input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }
        ) {
          projectV2Item { id }
        }
      }`,
      { projectId, itemId, fieldId: field.id, optionId },
    )
    core.info(`${key}: ${fieldName} set to '${optionName}'`)
  }

  await setSingleSelect(FIELD_PRIORITY, priority)
  if (status !== '') {
    await setSingleSelect(FIELD_STATUS, status)
  }

  const current = await octokit.graphql<ItemValueQuery>(
    `query ($itemId: ID!, $field: String!) {
      node(id: $itemId) {
        ... on ProjectV2Item {
          value: fieldValueByName(name: $field) {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
        }
      }
    }`,
    { itemId, field: FIELD_SQUAD },
  )
  const currentSquad = current.node?.value?.name
  if (currentSquad) {
    core.info(`${key}: ${FIELD_SQUAD} already '${currentSquad}' — left unchanged`)
  } else {
    // The default squad exists so the issue cannot get lost off every team's view.
    await setSingleSelect(FIELD_SQUAD, squadDefault)
  }

  core.setOutput('item_id', itemId)
}

void run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
