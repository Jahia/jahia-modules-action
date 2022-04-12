import * as core from '@actions/core'
import * as exec from '@actions/exec'

// import {wait} from './wait'

import {setEnvironmentVariables, displaySystemInfo} from './init'

async function run(): Promise<void> {
  try {
    await setEnvironmentVariables()

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
