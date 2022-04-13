import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function copyRunArtifacts(
  containerName: string,
  desinationPath: string
): Promise<void> {
  core.startGroup(
    '🐋 Export containers artifacts (reports, secreenshots, videos) '
  )

  await runShellCommands(
    [`docker cp ${containerName}:/home/jahians/results ${desinationPath}`],
    'artifacts/cypress-artifacts.log'
  )

  core.endGroup()
}
