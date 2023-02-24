import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function stopDockerEnvironment(
  testsFolder: string,
  loggingMode: string
): Promise<void> {
  core.info(`Listing all containers that are still running`)
  await runShellCommands([`docker ps`], 'artifacts/stop.log', {
    cwd: testsFolder,
    ignoreReturnCode: true,
    loggingMode
  })

  core.info(`Stopping all running containers`)
  await runShellCommands([`docker ps -aq | xargs docker stop | xargs docker rm`], 'artifacts/stop.log', {
    cwd: testsFolder,
    ignoreReturnCode: true,
    loggingMode
  })

  core.info(`Prunning all images and containers`)
  await runShellCommands([`docker system prune -a -f`], 'artifacts/stop.log', {
    cwd: testsFolder,
    ignoreReturnCode: true,
    loggingMode
  })  

  core.info(`Listing all containers running (if any)`)
  await runShellCommands([`docker ps`], 'artifacts/stop.log', {
    cwd: testsFolder,
    ignoreReturnCode: true,
    loggingMode
  })

}
