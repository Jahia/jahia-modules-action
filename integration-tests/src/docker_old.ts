import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

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

// See: https://github.com/docker/login-action/blob/master/src/docker.ts
export async function login(username: string, password: string): Promise<void> {
  core.startGroup('🐋 Docker login')
  if (!username || !password) {
    throw new Error('Username and password required')
  }

  const loginArgs: Array<string> = ['login', '--password-stdin']
  loginArgs.push('--username', username)

  core.info(`Logging into Docker Hub...`)

  await exec
    .getExecOutput('docker', loginArgs, {
      ignoreReturnCode: true,
      silent: true,
      input: Buffer.from(password)
    })
    .then(res => {
      if (res.stderr.length > 0 && res.exitCode != 0) {
        throw new Error(res.stderr.trim())
      }
      core.info(`Login Succeeded!`)
    })
  core.endGroup()
}

export async function startDockerEnvironment(
  ciStartupScript: string,
  dockerComposeFile: string
): Promise<void> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🐋 Starting the Docker environment')

    const startupFile = path.join(
      process.env.GITHUB_WORKSPACE,
      process.env.TESTS_PATH,
      ciStartupScript
    )

    const composeFile = path.join(
      process.env.GITHUB_WORKSPACE,
      process.env.TESTS_PATH,
      dockerComposeFile
    )

    if (fs.existsSync(startupFile)) {
      core.info(`Starting environment using startup script: ${startupFile}`)
      await runShellCommands([`bash ${startupFile}`], 'artifacts/startup.log')
    } else if (fs.existsSync(composeFile)) {
      core.info(`Starting environment using compose file: ${composeFile}`)
      await runShellCommands([`docker`], 'artifacts/startup.log')
    } else {
      core.setFailed(
        `Unable to find environment startup instructions. Could not find startup script (${startupFile}) NOR compose file ${composeFile}`
      )
    }
    core.endGroup()
  }
}
