import * as core from '@actions/core'
import * as exec from '@actions/exec'
import {download} from './artifacts'

// import {wait} from './wait'

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
      await download('build-artifacts')
    }

    // Prepare the export folder
    await createFolder(`${core.getInput('tests_path')}artifacts`)
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
