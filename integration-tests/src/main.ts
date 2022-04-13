import * as core from '@actions/core'
import {downloadArtifact, prepareBuildArtifact} from './artifacts'
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

    // Download the build artifact
    if (core.getInput('should_use_build_artifacts') === 'true') {
      await downloadArtifact('build-artifacts')
    }

    // Prepare the export folder
    await createFolder(`${core.getInput('tests_path')}artifacts`)

    // Prepare the build artifacts to include them in the docker image
    if (core.getInput('should_skip_artifacts') === 'false') {
      await prepareBuildArtifact(core.getInput('tests_path'))
    }
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
