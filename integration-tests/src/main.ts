import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {
  downloadArtifact,
  prepareBuildArtifact,
  uploadArtifact
} from './artifacts'
import {
  buildDockerTestImage,
  copyRunArtifacts,
  login,
  pullDockerImages,
  startDockerEnvironment
} from './docker'
import {
  setEnvironmentVariables,
  displaySystemInfo,
  installTooling
} from './init'

async function run(): Promise<void> {
  try {
    if (!process.env.GITHUB_WORKSPACE) {
      return
    }

    // Set the various project folders
    const rootProjectFolder = process.env.GITHUB_WORKSPACE
    if (!fs.existsSync(rootProjectFolder))
      core.setFailed(
        `Folder (rootProjectFolder) does not exist: ${rootProjectFolder}`
      )

    const testsFolder = path.join(
      rootProjectFolder,
      core.getInput('tests_path')
    )
    if (!fs.existsSync(testsFolder))
      core.setFailed(`Folder (testsFolder) does not exist: ${testsFolder}`)

    const artifactsFolder = path.join(testsFolder, 'artifacts')
    if (!fs.existsSync(artifactsFolder)) {
      core.info(`📁 Creating folder: ${artifactsFolder}`)
      fs.mkdirSync(artifactsFolder)
    }
    if (!fs.existsSync(artifactsFolder))
      core.setFailed(
        `Folder (artifactsFolder) does not exist: ${artifactsFolder}`
      )

    // Set environment variables from parameters
    await setEnvironmentVariables()

    // Install various tools (such as jahia-reporter) needed for the workflow
    await installTooling()

    // Display important versions and environment variables
    await displaySystemInfo()

    // Docker login
    await login(
      core.getInput('docker_username'),
      core.getInput('docker_password')
    )

    // Download the build artifact
    if (core.getInput('should_use_build_artifacts') === 'true') {
      await downloadArtifact('build-artifacts')
    }

    // Prepare the build artifacts to include them in the docker image
    if (core.getInput('should_skip_artifacts') === 'false') {
      await prepareBuildArtifact(rootProjectFolder, testsFolder)
    }

    // Build the test image
    if (core.getInput('should_build_testsimage') === 'true') {
      await buildDockerTestImage(
        core.getInput('tests_path'),
        core.getInput('tests_container_branch'),
        core.getInput('tests_image')
      )
    }

    // Pull the latest version of Jahia and jCustomer and print docker images cache to console
    await pullDockerImages(
      core.getInput('jahia_image'),
      core.getInput('jcustomer_image')
    )

    // Spin-up the containers
    await startDockerEnvironment(
      testsFolder,
      core.getInput('ci_startup_script'),
      core.getInput('docker_compose_file')
    )

    // Export containers artifacts (reports, secreenshots, videos)
    await copyRunArtifacts(
      core.getInput('tests_container_name'),
      artifactsFolder
    )

    // Finally, upload the artifacts
    await uploadArtifact(
      core.getInput('artifact_name'),
      artifactsFolder,
      Number(core.getInput('artifact_retention'))
    )
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
