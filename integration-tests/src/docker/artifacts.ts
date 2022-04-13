import * as core from '@actions/core'
import path from 'path/posix'

import {runShellCommands} from '../utils/system'

export async function copyRunArtifacts(
  containerName: string,
  desinationPath: string
): Promise<void> {
  core.startGroup(
    '🐋 Export containers artifacts (reports, secreenshots, videos, logs) '
  )

  await runShellCommands(
    [`docker cp ${containerName}:/home/jahians/results ${desinationPath}`],
    'artifacts/cypress-artifacts.log'
  )

  await runShellCommands(
    [`docker stats --all --no-stream`],
    'artifacts/results/cypress-stats.log'
  )

  await runShellCommands(
    [`docker-compose logs -t --tail="all" `],
    'artifacts/results/all-containers.log'
  )

  await runShellCommands([`docker logs jahia`], 'artifacts/results/jahia.log')

  await runShellCommands(
    [`docker logs ${containerName}`],
    `artifacts/results/${containerName}.log`
  )

  await runShellCommands([
    `docker ${path.join(desinationPath, `docker.log`)} ${path.join(
      desinationPath,
      `results/docker.log`
    )}`
  ])

  core.endGroup()
}
