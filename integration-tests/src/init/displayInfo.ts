import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function displaySystemInfo(): Promise<any> {
  core.startGroup(
    '🛠️ Displaying important environment variables and system info'
  )

  const runCommands: Array<string> = [
    'node -v',
    'npm -v',
    'jahia-reporter -v',
    'printenv'
  ]

  await runShellCommands(runCommands)

  core.endGroup()
}
