import * as core from '@actions/core'
import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

interface JahiaReporterPagerduty {
  service: string
  pdApiKey: string
  pdReporterEmail: string
  pdReporterId: string
  googleSpreadsheetId: string
  googleClientEmail: string
  googleApiKey: string
}

export async function createPagerdutyIncident(
  testsPath: string,
  options: JahiaReporterPagerduty
): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  let command = 'jahia-reporter pagerduty:incident'

  if (fs.existsSync(reportsPath)) {
    command += ` --sourcePath="${reportsPath}"`
    command += ' --sourceType="xml"'
  } else {
    core.info(`ERROR: The following path does not exist: ${reportsPath} pagerduty incident will not be based on test results`)
    command += ' --incidentMessage="Unable to find test folder, the tests were likely interrupted"'
  }
  command += ` --pdApiKey="${options.pdApiKey}"`
  command += ` --pdReporterEmail="${options.pdReporterEmail}"`
  command += ` --pdReporterId="${options.pdReporterId}"`
  command += ` --pdTwoStepsAssign`
  command += ` --googleSpreadsheetId="${options.googleSpreadsheetId}"`
  command += ` --googleClientEmail="${options.googleClientEmail}"`
  command += ` --googleApiKey="${options.googleApiKey}"`
  command += ` --googleUpdateState`
  command += ` --service="${options.service}"`
  command += ` --sourceUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

  await runShellCommands([command], null, {printCmd: false})
}
