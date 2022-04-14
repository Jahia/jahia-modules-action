import * as core from '@actions/core'

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
  core.exportVariable('TESTS_PATH', core.getInput('tests_path'))

  if (process.env.GITHUB_REF) {
    const branchName = process.env.GITHUB_REF.split('/')
      .slice(2)
      .join('/')
      .replace(/\//g, '-')
    core.exportVariable('CURRENT_BRANCH', branchName)
  }
}
