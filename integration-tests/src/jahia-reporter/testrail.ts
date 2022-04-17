import * as path from 'path'

import {runShellCommands} from '../utils/system'

interface JahiaReporterTestrail {
  testrailUsername: string
  testrailPassword: string
  testrailProject: string
  testrailMilestone: string
}

export async function publishToTestrail(
  testsPath: string,
  options: JahiaReporterTestrail
): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  let command = 'jahia-reporter testrail'
  command += ` --testrailUsername="${options.testrailUsername}"`
  command += ` --testrailPassword="${options.testrailPassword}"`
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ` --projectName="${options.testrailProject}"`
  command += ` --milestone="${options.testrailMilestone}"`
  command += ` --defaultRunDescription="This test was executed on Github Actions, ${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

  await runShellCommands([command], null, {printCmd: false})
}
