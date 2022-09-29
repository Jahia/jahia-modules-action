import * as core from '@actions/core'

import simpleGit from 'simple-git'

import {runShellCommands} from '../utils/system'
import path from "path";
import fs from "fs";

export async function buildDockerTestImage(
  testsFolder: string,
  ciBuildScript: string,
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  const buildFile = path.join(testsFolder, ciBuildScript)
  const git = simpleGit({
    baseDir: `${testsPath}`
  })
  const currentBranch = git.branch(['-v', '-a'])
  core.info(JSON.stringify(currentBranch))
  if (testsContainerBranch !== '') {
    core.info(`Switching repository to branch: ${testsContainerBranch}`)
    await git.checkout(testsContainerBranch)
  }

  if (!fs.existsSync(buildFile)) {
    const runCommands: Array<string> = [
      `docker build -t ${testsImage} ${testsPath}.`,
      `docker save -o ${testsPath}/tests_image.tar ${testsImage}`
    ]

    await runShellCommands(runCommands)
  }
}
