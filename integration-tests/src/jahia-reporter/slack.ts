import * as core from '@actions/core'
import * as path from 'path'
import * as fs from 'fs'

import {runShellCommands} from '../utils/system'

interface JahiaReporterSlack {
  channelId: string
  channelAllId: string
  token: string
}

export async function sendSlackNotification(
  testsPath: string,
  reportType: string,
  options: JahiaReporterSlack
): Promise<any> {
  const moduleFilepath = path.join(
    testsPath,
    'artifacts/results/installed-jahia-modules.json'
  )
  if (fs.existsSync(testsPath)) {
    let command = 'jahia-reporter slack'
    command += ` --sourcePath="${testsPath}"`
    command += ` --sourceType="${reportType}"`
    command += ` --channelId="${options.channelId}"`
    command += ` --channelAllId="${options.channelAllId}"`
    command += ` --token="${options.token}"`
    command += ` --skipSuccessful`
    command += ` --moduleFilepath="${moduleFilepath}"`
    command += ` --msgAuthor="Github Actions (${process.env.GITHUB_REPOSITORY})"`
    command += ` --runUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

    await runShellCommands([command], null, {printCmd: false})
  } else {
    core.info(`ERROR: The following path does not exist: ${testsPath}, slack message will not be sent`)
  }  
}
