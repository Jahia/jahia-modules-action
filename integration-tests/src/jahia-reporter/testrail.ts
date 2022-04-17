import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

interface JahiaReporterTestrail {
  testrailUsername: string
  testrailPassword: string
  testrailProject: string
  testrailMilestone: string
}

export async function publishToTestrail(
  testsPath: string,
  options: JahiaReporterTestrail
): Promise<any> {
  const reportsPath = path.join(testsPath, 'artifacts/results/xml_reports')
  const testrailLinkFile = path.join(
    testsPath,
    'artifacts/results/testrail_link'
  )

  let command = 'jahia-reporter testrail'
  command += ` --testrailUsername="${options.testrailUsername}"`
  command += ` --testrailPassword="${options.testrailPassword}"`
  command += ` --sourcePath="${reportsPath}"`
  command += ' --sourceType="xml"'
  command += ` --projectName="${options.testrailProject}"`
  command += ` --milestone="${options.testrailMilestone}"`
  command += ` --defaultRunDescription="This test was executed on Github Actions, ${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`
  command += ` --linkRunFile="${testrailLinkFile}"`

  await runShellCommands([command], null, {printCmd: false})

  if (fs.statSync(testrailLinkFile).isFile()) {
    const rawFile = fs.readFileSync(testrailLinkFile, 'utf8')
    core.notice(`Testrail run available at: ${rawFile.toString()}`)
  }
}
