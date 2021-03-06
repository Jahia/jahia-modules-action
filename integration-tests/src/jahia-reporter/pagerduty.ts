import * as path from 'path'

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
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
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
