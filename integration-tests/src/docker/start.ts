import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

export async function startDockerEnvironment(
  testsFolder: string,
  ciStartupScript: string,
  dockerComposeFile: string,
  loggingMode: string,
  timeoutMinutes: number
): Promise<void> {
  const startupFile = path.join(testsFolder, ciStartupScript)
  const composeFile = path.join(testsFolder, dockerComposeFile)
  const jahiaCliConfig = path.join(testsFolder, 'jahia-cli.config.yml')

  // Note that we're ignoring the return code on purpose.
  // The last step of the action will take care of verifying
  // if execution was successful

  if (fs.existsSync(jahiaCliConfig)) {
    // If a file called jahia-cli.config.yml is present in the tests folder, then jahia-cli will be used to build the image
    let createEnvironment = `jahia-cli environment:create -c ${jahiaCliConfig}`
    await runShellCommands([createEnvironment], 'artifacts/create.log', {
      cwd: testsFolder,
      ignoreReturnCode: true
    })

    let startTests = `jahia-cli tests:run -c ${jahiaCliConfig} --env JAHIA_HOST=jahia --env JAHIA_URL=http://jahia:8080 `
    await runShellCommands([startTests], 'artifacts/start-tests.log', {
      cwd: testsFolder,
      ignoreReturnCode: true
    })
  } else if (fs.existsSync(startupFile)) {
    core.info(`Starting environment using startup script: ${startupFile}`)

    try {
      await runShellCommands([`bash ${startupFile}`], 'artifacts/startup.log', {
        cwd: testsFolder,
        ignoreReturnCode: true,
        loggingMode,
        timeoutMinutes,
        // pass the docker compose file to the startup script
        env: {...process.env, DOCKER_COMPOSE_FILE: composeFile}
      })
    } catch (error) {
      core.error(`Failed to execute startup script: ${error}`)
      throw error
    }
  } else if (fs.existsSync(composeFile)) {
    core.info(`Starting environment using compose file: ${composeFile}`)
    try {
      await runShellCommands(
        [`docker-compose -f ${composeFile} up --abort-on-container-exit`],
        'artifacts/startup.log',
        {cwd: testsFolder, ignoreReturnCode: true, loggingMode, timeoutMinutes}
      )
    } catch (error) {
      core.error(`Failed to execute Docker Compose command: ${error}`)
      throw error
    }
  } else {
    core.setFailed(
      `Unable to find environment startup instructions. Could not find startup script (${startupFile}) NOR compose file ${composeFile}`
    )
  }
}
