import * as core from '@actions/core'
import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

export async function showTestsSummary(testsPath: string): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  if (fs.existsSync(reportsPath)) {
    let command = 'jahia-reporter summary'
    command += ` --sourcePath="${reportsPath}"`
    command += ' --sourceType="xml"'
    command += ' -s'
  
    await runShellCommands([command])
  } else {
    core.info(`ERROR: The following path does not exist: ${reportsPath}, summary will not be displayed`)
  }
}
