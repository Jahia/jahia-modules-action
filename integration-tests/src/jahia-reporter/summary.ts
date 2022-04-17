import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function showTestsSummary(testsPath: string): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  let command = 'jahia-reporter summary'
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ' -s'

  await runShellCommands([command], null, {printCmd: false})
}
