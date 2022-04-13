import * as core from '@actions/core'
import {
  downloadArtifact,
  prepareBuildArtifact,
  uploadArtifact
} from './artifacts'
import {buildDockerTestImage, login, pullDockerImages} from './docker'
import {
  setEnvironmentVariables,
  displaySystemInfo,
  installTooling,
  createFolder
} from './init'

async function run(): Promise<void> {
  try {
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

    // Prepare the export folder
    await createFolder(`${core.getInput('tests_path')}artifacts`)

    // Prepare the build artifacts to include them in the docker image
    if (core.getInput('should_skip_artifacts') === 'false') {
      await prepareBuildArtifact('.', core.getInput('tests_path'))
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

    // Finally, upload the artifacts
    await uploadArtifact(core.getInput('artifact_name'), 'artifacts/')
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
