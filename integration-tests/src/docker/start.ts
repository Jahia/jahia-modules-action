import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function startDockerEnvironment(
  testsFolder: string,
  ciStartupScript: string,
  dockerComposeFile: string
): Promise<void> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🐋 Starting the Docker environment')

    const startupFile = path.join(testsFolder, ciStartupScript)

    const composeFile = path.join(testsFolder, dockerComposeFile)

    if (fs.existsSync(startupFile)) {
      core.info(`Starting environment using startup script: ${startupFile}`)
      await runShellCommands(
        [`bash ${startupFile})`],
        'artifacts/startup.log',
        {cwd: testsFolder}
      )
    } else if (fs.existsSync(composeFile)) {
      core.info(`Starting environment using compose file: ${composeFile}`)
      await runShellCommands(
        [`docker -f ${composeFile} up --abord-on-container-exit`],
        'artifacts/startup.log',
        {cwd: testsFolder}
      )
    } else {
      core.setFailed(
        `Unable to find environment startup instructions. Could not find startup script (${startupFile}) NOR compose file ${composeFile}`
      )
    }
    core.endGroup()
  }
}
