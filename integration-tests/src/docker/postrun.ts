import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function executePostrunScript(
  testsFolder: string,
  postrunScript: string
): Promise<void> {
  const postrunFile = path.join(testsFolder, postrunScript)

  // Note that we're ignoring the return code on purpose.
  // The last step of the action will take care of verifying
  // if execution was successful

  if (fs.existsSync(postrunFile)) {
    core.info(`Executing postrun script: ${postrunFile}`)
    await runShellCommands([`bash ${postrunFile}`], 'artifacts/postrun.log', {
      cwd: testsFolder,
      ignoreReturnCode: true
    })
  } else {
    core.info(`Postrun script not found: ${postrunFile}, skipping...`)
  }
}
