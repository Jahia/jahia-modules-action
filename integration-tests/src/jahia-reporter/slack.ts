import * as core from '@actions/core'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

interface JahiaReporterSlack {
  channelId: string
  channelAllId: string
  token: string
}

export async function sendSlackNotification(
  testsPath: string,
  options: JahiaReporterSlack
): Promise<any> {
  core.startGroup('🛠️ Send notification to Slack')

  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')
  const moduleFilepath = path.join(
    testsPath,
    'artifacts/results/installed-jahia-modules.json'
  )

  let command = 'jahia-reporter slack'
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ` --channelId="${options.channelId}"`
  command += ` --channelAllId="${options.channelAllId}"`
  command += ` --token="${options.token}"`
  command += ` --skipSuccessful`
  command += ` --moduleFilepath="${moduleFilepath}"`
  command += ` --msgAuthor="Github Actions (${process.env.GITHUB_REPOSITORY})"`
  command += ` --runUrl="${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`

  await runShellCommands([command], null, {printCmd: false})

  core.endGroup()
}
