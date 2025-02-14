import * as core from '@actions/core'
import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

interface JahiaReporterZencrepes {
  service: string
  webhookSecret: string
}

export async function sendResultsToZencrepes(
  testsPath: string,
  testsResultsPath: string,
  reportType: string,
  options: JahiaReporterZencrepes
): Promise<any> {
  const reportsPath = path.join(testsPath, testsResultsPath)
  const moduleFilepath = path.join(
    testsPath,
    'artifacts/results/installed-jahia-modules.json'
  )

  if (fs.existsSync(reportsPath)) {
    let command = 'jahia-reporter zencrepes'
    command += ` --sourcePath="${reportsPath}"`
    command += ` --sourceType="${reportType}"`
    command += ` --webhook="https://zencrepes.jahia.com/zqueue/testing/webhook"`
    command += ` --webhookSecret="${options.webhookSecret}"`
    command += ` --moduleFilepath="${moduleFilepath}"`
    command += ` --name="${options.service}"`
    command += ` --runUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

    await runShellCommands([command], null, {printCmd: false})
  } else {
    core.info(
      `ERROR: The following path does not exist: ${reportsPath}, report will not be submitted to ZenCrepes`
    )
  }
}
