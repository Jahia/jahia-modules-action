import {getInput} from '@actions/core'
import type {Inputs} from './types.js'

export const readInputs = (): Inputs => {
  const versions = getInput('versions') || 'store'
  if (versions !== 'store' && versions !== 'shipped')
    throw new Error(`versions is store or shipped, not ${versions}`)
  return {
    jahiaVersion: getInput('jahia_version', {required: true}),
    versions,
    storeUrl: getInput('store_url') || 'https://store.jahia.com/en/sites/private-app-store',
    nexusUsername: getInput('nexus_username'),
    nexusPassword: getInput('nexus_password'),
    provisioningPath: getInput('provisioning_path') || 'modules-provisioning.yml',
    matrixPath: getInput('matrix_path') || 'compat-matrix.json'
  }
}
