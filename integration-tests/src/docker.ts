import * as core from '@actions/core'
import * as exec from '@actions/exec'

import simpleGit from 'simple-git'

import {runShellCommands} from './utils/system'

export async function buildDockerTestImage(
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  core.startGroup('🐋 Build test docker container')

  core.info(JSON.stringify(process.env.GITHUB_WORKSPACE))
  const git = simpleGit({
    baseDir: `${testsPath}`
  })
  const currentBranch = git.branch(['-v', '-a'])
  core.info(JSON.stringify(currentBranch))
  if (testsContainerBranch !== '') {
    core.info(`Switching repository to branch: ${testsContainerBranch}`)
    await git.checkout(testsContainerBranch)
  }

  const runCommands: Array<string> = [
    `docker build -t ${testsImage} ${testsPath}.`,
    `docker save -o ${testsPath}/tests_image.tar ${testsImage}`
  ]

  await runShellCommands(runCommands)

  core.endGroup()
}

export async function pullDockerImages(
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string,
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
  runCommands.push(`docker pull ${jCustomerImage}`)

  await runShellCommands(runCommands, 'artifacts/docker.log')

  core.endGroup()
}
