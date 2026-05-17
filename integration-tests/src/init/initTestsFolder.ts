import * as core from '@actions/core'

import path from 'path'
import fs from 'fs'

import {runShellCommands} from '../utils/system'

export async function initTestsFolder(testsFolder: string): Promise<any> {
  const jahiaCliConfig = path.join(testsFolder, 'jahia-cli.config.yml')
  if (fs.existsSync(jahiaCliConfig)) {
    core.info(
      `Found jahia-cli.config.yml in tests folder (${jahiaCliConfig}), fetching the scaffolding using jahia-cli`
    )
    await runShellCommands([
      `jahia-cli tests:init -c ${jahiaCliConfig} --path ${testsFolder}/`
    ])
  } else {
    core.info(
      `No jahia-cli.config.yml found in tests folder (${jahiaCliConfig}), skipping scaffolding fetch from jahia-cypress`
    )
  }
}
