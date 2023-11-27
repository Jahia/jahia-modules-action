import * as core from '@actions/core'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

export async function showTestsSummary(testsPath: string, reportType: string): Promise<any> {
  if (fs.existsSync(testsPath)) {
    let command = 'jahia-reporter summary'
    command += ` --sourcePath="${testsPath}"`
    command += ` --sourceType="${reportType}"`
    command += ' -s'
  
    await runShellCommands([command])
  } else {
    core.info(`ERROR: The following path does not exist: ${testsPath}, summary will not be displayed`)
  }
}
