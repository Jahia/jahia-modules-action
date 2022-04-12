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
    core.exportVariable('MANIFEST', core.getInput('tests_manifest'))
    core.exportVariable('JAHIA_IMAGE', core.getInput('jahia_image'))
    core.exportVariable('JAHIA_LICENSE', core.getInput('jahia_license'))
    core.exportVariable(
      'JAHIA_CLUSTER_ENABLED',
      core.getInput('jahia_cluster_enabled')
    )
    core.exportVariable('TESTS_IMAGE', core.getInput('tests_image'))
    core.exportVariable('JCUSTOMER_IMAGE', core.getInput('jcustomer_image'))
    core.exportVariable(
      'ELASTICSEARCH_IMAGE',
      core.getInput('elasticsearch_image')
    )
    core.exportVariable('NEXUS_USERNAME', core.getInput('nexus_username'))
    core.exportVariable('NEXUS_PASSWORD', core.getInput('nexus_password'))
    core.exportVariable('DOCKER_USERNAME', core.getInput('docker_username'))

    const moduleId: string = core.getInput('module_id')

    core.startGroup(
      '🛠️ Displaying important environment variables and system info'
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
