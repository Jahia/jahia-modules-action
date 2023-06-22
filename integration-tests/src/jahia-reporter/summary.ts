import * as core from '@actions/core'

import * as path from 'path'
import fs from 'fs'

import {runShellCommands} from '../utils/system'

export async function showTestsSummary(testsPath: string): Promise<any> {
  if (!fs.existsSync(testsPath)) {
    core.info(`${testsPath} does not exists, skipping jahia-reporter summary`)
    return
  }

  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')

  let command = 'jahia-reporter summary'
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ' -s'

  await runShellCommands([command])
}
