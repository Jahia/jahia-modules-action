import * as core from '@actions/core'

import * as path from 'path'
import fs from 'fs'

import {runShellCommands} from '../utils/system'

interface JahiaReporterZencrepes {
  service: string
  webhookSecret: string
}

export async function sendResultsToZencrepes(
  testsPath: string,
  options: JahiaReporterZencrepes
): Promise<any> {
  if (!fs.existsSync(testsPath)) {
    core.info(`${testsPath} does not exists, skipping zencrepes report`)
    return
  }

  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')
  const moduleFilepath = path.join(
    testsPath,
    'artifacts/results/installed-jahia-modules.json'
  )

  let command = 'jahia-reporter zencrepes'
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ` --webhook="https://zencrepes.jahia.com/zqueue/testing/webhook"`
  command += ` --webhookSecret="${options.webhookSecret}"`
  command += ` --moduleFilepath="${moduleFilepath}"`
  command += ` --name="${options.service}"`
  command += ` --runUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

  await runShellCommands([command], null, {printCmd: false})
}
