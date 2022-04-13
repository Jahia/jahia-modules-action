import * as core from '@actions/core'
import * as exec from '@actions/exec'

import {runShellCommands} from './utils/system'

export async function buildDockerTestImage(
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  core.startGroup('🐋 Build test docker container')

  const runCommands: Array<string> = [
    // `git checkout ${testsContainerBranch}`,
    `docker build -t ${testsImage} ${testsPath}.`,
    `docker save -o ${testsPath}/tests_image.tar ${testsImage}`
  ]

  await runShellCommands(runCommands)

  core.endGroup()
}
