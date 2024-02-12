import * as core from '@actions/core'
import path from 'path/posix'
import fs from "fs";

import {runShellCommands} from '../utils/system'

export async function copyRunArtifacts(
  containerName: string,
  desinationPath: string,
  testsFolder: string
): Promise<void> {
  await runShellCommands(
    [`docker cp ${containerName}:/home/jahians/results ${desinationPath}`],
    'artifacts/cypress-artifacts.log',
    {
      ignoreReturnCode: true,
    }
  )

  // The command above might fail (for example if the test container failed building)
  // In such a case, it might be necessary to create the results folder
  if (!fs.existsSync(path.join(desinationPath, 'results/'))) {
    fs.mkdirSync(path.join(desinationPath, 'results/'))
  }

  await runShellCommands(
    [`docker stats --all --no-stream`],
    'artifacts/results/cypress-stats.log',
    {
      ignoreReturnCode: true,
    }
  )

  await runShellCommands(
    [`docker-compose logs -t --tail="all" `],
    'artifacts/results/all-containers.log',
    {
      cwd: testsFolder,
      ignoreReturnCode: true,
      silent: true
    }
  )

  await runShellCommands([`docker logs jahia`], 'artifacts/results/jahia.log', {
    ignoreReturnCode: true,
    silent: true
  })

  await runShellCommands(
    [`docker logs ${containerName}`],
    `artifacts/results/${containerName}.log`,
    {
      ignoreReturnCode: true,
      silent: true
    }
  )

  await runShellCommands([
    `cp ${path.join(desinationPath, `docker.log`)} ${path.join(
      desinationPath,
      `results/docker.log`
    )}`
  ], 
  null, {
    ignoreReturnCode: true
  })
}
