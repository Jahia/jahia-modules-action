import * as core from '@actions/core'
import {wait} from './wait'

async function run(): Promise<void> {
  try {
    const moduleId: string = core.getInput('module_id')
    core.info(`Testing module ${moduleId} ...`) // debug is only output if you set the secret `ACTIONS_STEP_DEBUG` to true

    // core.debug(new Date().toTimeString())
    // await wait(parseInt(ms, 10))
    // core.debug(new Date().toTimeString())

    // core.setOutput('time', new Date().toTimeString())
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
