import * as core from '@actions/core'

import {runShellCommands} from '../utils/system'

export async function installTooling(): Promise<any> {
  core.startGroup('🛠️ Install runtime tooling')
  await runShellCommands(['npm install -g @jahia/jahia-reporter'])
  core.endGroup()
}
