import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function pullDockerImages(
  jahiaImage: string,
  jCustomerImage: string
): Promise<any> {
  core.startGroup(
    '🐋 Pull the latest version of Jahia and jCustomer and print docker images cache to console'
  )

  // Get list of docker images in local cache BEFORE the pull
  const runCommands: Array<string> = [`docker images --digests --all`]

  if (jahiaImage !== '') {
    runCommands.push(`docker pull ${jahiaImage}`)
  }

  if (jCustomerImage !== '') {
    runCommands.push(`docker pull ${jCustomerImage}`)
  }

  // Get list of docker images in local cache AFTER the pull
  runCommands.push(`docker images --digests --all`)

  await runShellCommands(runCommands, 'artifacts/docker.log')

  core.endGroup()
}
