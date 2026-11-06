import * as core from '@actions/core'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

// GitHub keeps 10 error annotations for each step, and the failure of the step takes the last one
const MAX_ANNOTATIONS = 9

// testsFolder is the folder of the tests, relative to the root of the repository
export async function annotateFailedTests(
  testsPath: string,
  reportType: string,
  testsFolder: string
): Promise<any> {
  if (fs.existsSync(testsPath)) {
    let command = 'jahia-reporter github:annotations'
    command += ` --sourcePath="${testsPath}"`
    command += ` --sourceType="${reportType}"`
    command += ` --testsPath="${testsFolder}"`
    command += ` --maxAnnotations=${MAX_ANNOTATIONS}`
    command += ' -s'

    await runShellCommands([command])
  } else {
    core.info(
      `ERROR: The following path does not exist: ${testsPath}, annotations will not be written`
    )
  }
}
