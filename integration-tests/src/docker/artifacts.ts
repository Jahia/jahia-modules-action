import * as core from '@actions/core'

import * as exec from '@actions/exec'
import path from 'path/posix'
import fs from 'fs'

import {runShellCommands} from '../utils'

const silent = {silent: true}

export async function copyRunArtifacts(
  containerName: string,
  destinationPath: string,
  testsFolder: string,
  dockerComposeFile: string
): Promise<void> {
  const composeFile = path.join(testsFolder, dockerComposeFile)
  const jahiaCliConfig = path.join(testsFolder, 'jahia-cli.config.yml')
  if (fs.existsSync(jahiaCliConfig)) {
    // If a file called jahia-cli.config.yml is present in the tests folder, then jahia-cli will be used to fetch the artifacts
    await runShellCommands(
      [`jahia-cli tests:artifacts -o  ${destinationPath}`],
      'artifacts/tests-artifacts.log',
      {
        ignoreReturnCode: true
      }
    )
  } else {
    core.info(
      `No jahia-cli.config.yml found in tests folder (${jahiaCliConfig}), fetching artifacts using docker commands`
    )

    await runShellCommands(
      [`docker cp ${containerName}:/home/jahians/results ${destinationPath}`],
      'artifacts/cypress-artifacts.log',
      {
        ignoreReturnCode: true
      }
    )

    await runShellCommands(
      [`docker stats --all --no-stream`],
      'artifacts/results/cypress-stats.log',
      {
        ignoreReturnCode: true
      }
    )

    await runShellCommands(
      [`docker-compose -f ${composeFile} logs -t --tail="all" `],
      'artifacts/results/all-containers.log',
      {
        cwd: testsFolder,
        ignoreReturnCode: true,
        silent: true
      }
    )

    await exec
      .getExecOutput('docker', ['ps', '-a', '--format', '{{.Names}}'])
      .then(async (r: exec.ExecOutput) => {
        const output = r.stdout ?? ''
        const containers = output
          .split('\n')
          .map(s => s.trim())
          .filter(Boolean)

        for (const container of containers) {
          await runShellCommands(
            [`docker logs ${container}`],
            `artifacts/results/${container}.log`,
            silent
          )
        }
      })

    await runShellCommands(
      [
        `cp ${path.join(destinationPath, 'docker.log')} ${path.join(
          destinationPath,
          `results/docker.log`
        )}`
      ],
      null,
      silent
    )
  }
  core.info(`Listing artifacts content at: ${destinationPath}`)
  await runShellCommands([`tree ${destinationPath}`], 'artifacts/tree.log', {
    ignoreReturnCode: true
  })
}
