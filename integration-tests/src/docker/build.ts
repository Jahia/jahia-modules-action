import * as core from '@actions/core'

import simpleGit from 'simple-git'

import {runShellCommands} from '../utils/system'
import path from 'path'
import fs from 'fs'

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

  const cacheEnabled = core.getInput('docker_build_cache_enabled') === 'true'
  const cacheScope = core.getInput('docker_build_cache_scope') || 'docker-build'

  // Set environment variables for cache configuration
  // These can be used by build scripts (in particular ci.build.sh from jahia-cypress)
  const buildEnv = {
    ...process.env,
    DOCKER_BUILD_CACHE_ENABLED: cacheEnabled ? 'true' : 'false',
    DOCKER_BUILD_CACHE_SCOPE: cacheScope,
    DOCKER_BUILDX_CACHE_FROM: `type=gha,scope=${cacheScope}`,
    DOCKER_BUILDX_CACHE_TO: `type=gha,mode=max,scope=${cacheScope}`
  }

  if (!fs.existsSync(buildScript)) {
    core.info(`Building test image using docker`)

    let buildCommand
    let saveCommand = `docker save -o tests_image.tar ${testsImage}`

    if (cacheEnabled) {
      core.info(`🔄 Docker build cache is enabled (scope=${cacheScope})`)
      // Use buildx with GitHub Actions cache
      buildCommand = `docker buildx build --cache-from type=gha,scope=${cacheScope} --cache-to type=gha,mode=max,scope=${cacheScope} -t ${testsImage} --load .`
    } else {
      buildCommand = `docker build -t ${testsImage} .`
    }

    const runCommands: Array<string> = [buildCommand, saveCommand]
    await runShellCommands(runCommands, 'artifacts/build.log', {
      cwd: testsFolder,
      ignoreReturnCode: true,
      env: buildEnv
    })
  } else {
    core.info(`Building test image using script: ${buildScript}`)
    if (cacheEnabled) {
      core.info(`🔄 Docker build cache is enabled (scope=${cacheScope})`)
      core.info(`Cache settings are available via environment variables:`)
      core.info(`  DOCKER_BUILD_CACHE_ENABLED=${buildEnv.DOCKER_BUILD_CACHE_ENABLED}`)
      core.info(`  DOCKER_BUILD_CACHE_SCOPE=${buildEnv.DOCKER_BUILD_CACHE_SCOPE}`)
      core.info(`  DOCKER_BUILDX_CACHE_FROM=${buildEnv.DOCKER_BUILDX_CACHE_FROM}`)
      core.info(`  DOCKER_BUILDX_CACHE_TO=${buildEnv.DOCKER_BUILDX_CACHE_TO}`)
    }
    await runShellCommands([`bash ${ciBuildScript}`], 'artifacts/build.log', {
      cwd: testsFolder,
      ignoreReturnCode: true,
      env: buildEnv
    })
  }
}
