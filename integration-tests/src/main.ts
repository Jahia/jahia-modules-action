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
    // Prepare the export folder
    if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
      const artifactsFolder = path.join(
        process.env.GITHUB_WORKSPACE,
        process.env.TESTS_PATH,
        'artifacts'
      )
      if (!fs.existsSync(artifactsFolder)) {
        core.info(`📁 Creating folder: ${artifactsFolder}`)
        fs.mkdirSync(artifactsFolder)
      }
    }

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
      await prepareBuildArtifact('', '')
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
      core.getInput('ci_startup_script'),
      core.getInput('docker_compose_file')
    )

    // Finally, upload the artifacts
    await uploadArtifact(core.getInput('artifact_name'), 'artifacts')
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
