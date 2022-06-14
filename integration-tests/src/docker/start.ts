import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function startDockerEnvironment(
  testsFolder: string,
  ciStartupScript: string,
  dockerComposeFile: string
): Promise<void> {
  const startupFile = path.join(testsFolder, ciStartupScript)
  const composeFile = path.join(testsFolder, dockerComposeFile)

  // Note that we're ignoring the return code on purpose.
  // The last step of the action will take care of verifying
  // if execution was successful

  if (fs.existsSync(startupFile)) {
    core.info(`Starting environment using startup script: ${startupFile}`)
    await runShellCommands([`bash ${startupFile}`], 'artifacts/startup.log', {
      cwd: testsFolder,
      ignoreReturnCode: true
    })
  } else if (fs.existsSync(composeFile)) {
    core.info(`Starting environment using compose file: ${composeFile}`)
    await runShellCommands(
      [`docker-compose -f ${composeFile} up --abord-on-container-exit`],
      'artifacts/startup.log',
      {cwd: testsFolder, ignoreReturnCode: true}
    )
  } else {
    core.setFailed(
      `Unable to find environment startup instructions. Could not find startup script (${startupFile}) NOR compose file ${composeFile}`
    )
  }
}
