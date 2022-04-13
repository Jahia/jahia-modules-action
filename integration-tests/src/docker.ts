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
  const currentBranch = git.branch()
  core.info(JSON.stringify(currentBranch))
  if (testsContainerBranch !== '') {
    core.info(`Switching repository to branch: ${testsContainerBranch}`)
    await git.checkout(testsContainerBranch)
  }

  const runCommands: Array<string> = [
    // `git checkout ${testsContainerBranch}`,
    `docker build -t ${testsImage} ${testsPath}.`,
    `docker save -o ${testsPath}/tests_image.tar ${testsImage}`
  ]

  await runShellCommands(runCommands)

  core.endGroup()
}
