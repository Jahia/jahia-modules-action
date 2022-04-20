import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function installTooling(): Promise<any> {
  await runShellCommands([
    'npm install -g @jahia/jahia-reporter',
    'which rsync'
    // 'sudo apt-get update',
    // 'sudo apt-get install rsync'
  ])
}
