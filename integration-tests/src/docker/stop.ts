import * as core from '@actions/core'
import * as exec from '@actions/exec'

import {runShellCommands} from '../utils'

export async function stopDockerEnvironment(
  testsFolder: string,
  loggingMode: string
): Promise<void> {
  core.info(`Listing all containers at the end of the test`)
  await runShellCommands([`docker ps -a`], 'artifacts/stop.log', {
    cwd: testsFolder,
    ignoreReturnCode: true,
    loggingMode
  })

  core.info(`Stopping all running containers`)
  await exec
    .getExecOutput('docker', ['ps', '-aq'], {
      ignoreReturnCode: true,
      silent: true
    })
    .then(async res => {
      core.info(`Output of ps -aq ${JSON.stringify(res)}`)
      const containers = res.stdout.split(/\r?\n/)
      for (const container of containers.filter(c => c.length > 5)) {
        core.info(`Stopping container: ${container}`)
        await exec
          .getExecOutput('docker', ['stop', container], {
            ignoreReturnCode: true,
            silent: true
          })
          .then(res => {
            if (res.stderr.length > 0 && res.exitCode != 0) {
              core.info(`Unable to stop container: ${container}`)
            }
            core.info(`Container ${container} stopped`)
          })
      }
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
