import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'

import {runShellCommands} from './utils/system'

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
  core.startGroup('🛠️ Install runtime tooling')
  await runShellCommands(['npm install -g @jahia/jahia-reporter'])
  core.endGroup()
}

export async function displaySystemInfo(): Promise<any> {
  core.startGroup(
    '🛠️ Displaying important environment variables and system info'
  )

  const runCommands: Array<string> = [
    'node -v',
    'npm -v',
    'jahia-reporter -v',
    'printenv'
  ]

  await runShellCommands(runCommands)

  core.endGroup()
}

export async function createFolder(folder: string): Promise<any> {
  if (!fs.existsSync(folder)) {
    core.info(`📁 Creating folder: ${folder}`)
    fs.mkdirSync(folder)
  }
}
