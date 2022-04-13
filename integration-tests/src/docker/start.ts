import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function startDockerEnvironment(
  ciStartupScript: string,
  dockerComposeFile: string
): Promise<void> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🐋 Starting the Docker environment')

    const testFolder = path.join(
      process.env.GITHUB_WORKSPACE,
      process.env.TESTS_PATH
    )

    const startupFile = path.join(testFolder, ciStartupScript)

    const composeFile = path.join(testFolder, dockerComposeFile)

    if (fs.existsSync(startupFile)) {
      core.info(`Starting environment using startup script: ${startupFile}`)
      await runShellCommands(
        [`(cd ${testFolder}; bash ${startupFile})`],
        'artifacts/startup.log'
      )
    } else if (fs.existsSync(composeFile)) {
      core.info(`Starting environment using compose file: ${composeFile}`)
      await runShellCommands(
        [`docker -f ${composeFile} up --abord-on-container-exit`],
        'artifacts/startup.log'
      )
    } else {
      core.setFailed(
        `Unable to find environment startup instructions. Could not find startup script (${startupFile}) NOR compose file ${composeFile}`
      )
    }
    core.endGroup()
  }
}
