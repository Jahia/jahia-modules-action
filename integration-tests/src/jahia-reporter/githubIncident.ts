import * as core from '@actions/core'
import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

interface JahiaReporterGitHubIncident {
  service: string
  googleSpreadsheetId: string
  googleClientEmail: string
  googleApiKey: string
  githubToken: string
}

export async function createGitHubIncident(
  testsPath: string,
  reportType: string,
  options: JahiaReporterGitHubIncident
): Promise<any> {
  let command = 'jahia-reporter github:incident'

  if (fs.existsSync(testsPath)) {
    command += ` --sourcePath="${testsPath}"`
    command += ` --sourceType="${reportType}"`
  } else {
    core.info(
      `ERROR: The following path does not exist: ${testsPath} the github issue will not be based on test results`
    )
    command +=
      ' --incidentMessage="Unable to find test results, the tests were likely interrupted"'
  }
  command += ` --googleSpreadsheetId="${options.googleSpreadsheetId}"`
  command += ` --googleClientEmail="${options.googleClientEmail}"`
  command += ` --googleApiKey="${options.googleApiKey}"`
  command += ` --googleUpdateState`

  command += ` --githubToken="${options.githubToken}"`
  command += ` --githubRepository="${process.env.GITHUB_REPOSITORY}"`

  command += ` --incidentService="${options.service}"`
  command += ` --sourceUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

  await runShellCommands([command], null, {printCmd: false})
}
