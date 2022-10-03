import * as core from '@actions/core'

import simpleGit from 'simple-git'

import {runShellCommands} from '../utils/system'
import path from "path";
import fs from "fs";

export async function buildDockerTestImage(
  testsFolder: string,
  ciBuildScript: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  const buildScript = path.join(testsFolder, ciBuildScript)
  const git = simpleGit({
    baseDir: `${testsFolder}`
  })
  const currentBranch = git.branch(['-v', '-a'])
  core.info(JSON.stringify(currentBranch))
  if (testsContainerBranch !== '') {
    core.info(`Switching repository to branch: ${testsContainerBranch}`)
    await git.checkout(testsContainerBranch)
  }

  if (!fs.existsSync(buildScript)) {
    core.info(`Starting environment using docker build`)
    const runCommands: Array<string> = [
      `docker build -t ${testsImage} .`,
      `docker save -o tests_image.tar ${testsImage}`
    ]
    await runShellCommands(runCommands,
        'artifacts/build.log',
        {cwd: testsFolder, ignoreReturnCode: true})
  } else {
    core.info(`Starting environment using build script: ${buildScript}`)
    await runShellCommands(
        [`bash ${ciBuildScript}`],
        'artifacts/build.log',
        {cwd: testsFolder, ignoreReturnCode: true}
    )
  }
}
