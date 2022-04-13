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

  const otherCommands = [
    `docker stats --all --no-stream > ${path.join(
      desinationPath,
      'results/docker-stats.log'
    )}`,
    `docker-compose logs -t --tail="all" > ${path.join(
      desinationPath,
      'results/all-containers.log'
    )}`,
    `docker logs jahia > ${path.join(desinationPath, 'results/jahia.log')}`,
    `docker logs ${containerName} > ${path.join(
      desinationPath,
      `results/${containerName}.log`
    )}`,
    `cp ${path.join(desinationPath, `docker.log`)} ${path.join(
      desinationPath,
      `results/docker.log`
    )}`
  ]

  await runShellCommands(otherCommands, 'artifacts/copy-run-artifacts.log')

  core.endGroup()
}
