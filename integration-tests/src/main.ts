import * as core from '@actions/core'
import * as exec from '@actions/exec'

import {wait} from './wait'

let myOutput = ''
let myError = ''

const options: exec.ExecOptions = {}
options.listeners = {
  stdout: (data: Buffer) => {
    myOutput += data.toString()
  },
  stderr: (data: Buffer) => {
    myError += data.toString()
  }
}

async function run(): Promise<void> {
  try {
    const moduleId: string = core.getInput('module_id')

    core.startGroup(
      'Displaying important environment variables and system info'
    )
    core.info(`Testing module ${moduleId} ...`)
    await exec.exec('node', ['-v'], {...options, silent: true})
    core.info(`node -v: ${myOutput}`)
    core.endGroup()

    // core.debug(new Date().toTimeString())
    // await wait(parseInt(ms, 10))
    // core.debug(new Date().toTimeString())

    // core.setOutput('time', new Date().toTimeString())
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
