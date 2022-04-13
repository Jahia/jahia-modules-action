import * as core from '@actions/core'
import * as exec from '@actions/exec'

export async function setEnvironmentVariables(): Promise<any> {
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
}

export async function installTooling(): Promise<any> {
  let stdOut = ''
  let stdErr = ''
  const options: exec.ExecOptions = {}
  options.listeners = {
    stdout: (data: Buffer) => {
      stdOut += data.toString()
    },
    stderr: (data: Buffer) => {
      stdErr += data.toString()
    }
  }

  core.startGroup('🛠️ Install runtime tooling')
  await exec.exec('npm install -g @jahia/jahia-reporter', [], {
    ...options,
    silent: true
  })
  core.endGroup()
}

export async function displaySystemInfo(): Promise<any> {
  const runCommands: Array<string> = [
    'node -v',
    'npm -v',
    'jahia-reporter -v',
    'printenv'
  ]

  core.startGroup(
    '🛠️ Displaying important environment variables and system info'
  )

  for (const cmd of runCommands) {
    let stdOut = ''
    let stdErr = ''

    const options: exec.ExecOptions = {}
    options.listeners = {
      stdout: (data: Buffer) => {
        stdOut += data.toString()
      },
      stderr: (data: Buffer) => {
        stdErr += data.toString()
      }
    }
    await exec.exec(cmd, [], {...options, silent: true})
    core.info(`${cmd}: ${stdOut}${stdErr}`)
  }

  const moduleId: string = core.getInput('module_id')

  core.info(`Testing module ${moduleId} ...`)

  //   await exec.exec('echo ${DOCKER_USERNAME}', [], {...options, silent: true})
  //   core.info(`echo: ${myOutput}`)

  core.endGroup()
}
