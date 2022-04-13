import * as core from '@actions/core'
import * as exec from '@actions/exec'

// import {wait} from './wait'

import {
  setEnvironmentVariables,
  displaySystemInfo,
  installTooling
} from './init'

async function run(): Promise<void> {
  try {
    // Set environment variables from parameters
    await setEnvironmentVariables()

    // Install various tools (such as jahia-reporter) needed for the workflow
    await installTooling()

    // Display important versions and environment variables
    await displaySystemInfo()

    // core.debug(new Date().toTimeString())
    // await wait(parseInt(ms, 10))
    // core.debug(new Date().toTimeString())

    // core.setOutput('time', new Date().toTimeString())
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
