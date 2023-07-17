import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {runShellCommands} from '../utils/system'

interface JahiaReporterTestrail {
  testrailUsername: string
  testrailPassword: string
  testrailParentSection: string
  testrailProject: string
  testrailMilestone: string
}

interface TestrailMetadata {
  [key: string]: any;
}

export async function prepareTestrailMetadata(
  testsPath: string,
  testrailPlatformdata: string,
) {
  const platformDataFile = path.join(testsPath, 'artifacts/results/', testrailPlatformdata)
  let testrailMetadata: TestrailMetadata = {}
  testrailMetadata['custom_url'] = `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`

  if (fs.existsSync(platformDataFile) && fs.statSync(platformDataFile).isFile()) {
    const rawFile = fs.readFileSync(platformDataFile, 'utf8')
    const platformData = JSON.parse(rawFile.toString())

    core.info(`Parsed platform file: ${platformDataFile}`)
    if (platformData.platform !== undefined) {
      core.info(`Its content is: ${JSON.stringify(platformData.platform)}`)

      // In this section, we're statically defining the link between the
      // response from Jahia GraphQL API and the metadata file to be used
      // with testrail (this has to be defined somewhere)
      if (platformData.platform.jahia?.version?.release !== undefined) {
        testrailMetadata['version'] = platformData.platform.jahia?.version?.release
        if (platformData.platform.jahia?.version?.build !== undefined) {
          testrailMetadata['version'] += ` - Build: ${platformData.platform.jahia?.version?.build}`
        }        
      }

      if (platformData.platform.jahia?.database?.name !== undefined) {
        testrailMetadata['custom_database'] = platformData.platform.jahia?.database?.name
        if (platformData.platform.jahia?.database?.version !== undefined) {
          testrailMetadata['custom_database'] += ` - Version: ${platformData.platform.jahia?.database?.version}`
        }
      }

      if (platformData.platform.jahia?.system?.java?.runtimeName !== undefined) {
        testrailMetadata['custom_java'] = platformData.platform.jahia?.system?.java?.runtimeName
        if (platformData.platform.jahia?.system?.java?.runtimeVersion !== undefined) {
          testrailMetadata['custom_java'] += ` - Version: ${platformData.platform.jahia?.system?.java?.runtimeVersion}`
        }
      }

      if (platformData.platform.jahia?.system?.os?.name !== undefined) {
        testrailMetadata['custom_os'] = platformData.platform.jahia?.system?.os?.name
        if (platformData.platform.jahia?.system?.os?.architecture !== undefined) {
          testrailMetadata['custom_os'] += ` (${platformData.platform.jahia?.system?.os?.architecture})`
        }        
        if (platformData.platform.jahia?.system?.os?.version !== undefined) {
          testrailMetadata['custom_os'] += ` - Version: ${platformData.platform.jahia?.system?.os?.version}`
        }
      }
    } else {
      core.info(`Unable to find a platform object inside the file`)
    }
  } else {
    core.info(`Unable to parse platform data file: ${platformDataFile}`)
  }

  // Always write a testrail metadata file, even if there is no data
  const metadataFile = path.join(testsPath, 'artifacts/results/testrail-metadata.json')
  core.info(`Preparing to write: ${JSON.stringify(testrailMetadata)}`)
  core.info(`To file: ${metadataFile}`)
  fs.writeFileSync(
    metadataFile,
    JSON.stringify(testrailMetadata)
  )
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
  const metadataFile = path.join(testsPath, 'artifacts/results/testrail-metadata.json')

  if (fs.existsSync(reportsPath)) {
    let command = 'jahia-reporter testrail'
    command += ` --testrailUsername="${options.testrailUsername}"`
    command += ` --testrailPassword="${options.testrailPassword}"`
    command += ` --sourcePath="${reportsPath}"`
    command += ' --sourceType="xml"'
    command += ` --projectName="${options.testrailProject}"`
    command += ` --parentSection="${options.testrailParentSection}"`
    command += ` --milestone="${options.testrailMilestone}"`
    command += ` --defaultRunDescription="This test was executed on Github Actions, ${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}"`
    command += ` --testrailCustomResultFields="${metadataFile}"`
    command += ` --linkRunFile="${testrailLinkFile}"`
  
    await runShellCommands([command], null, {printCmd: false})
  } else {
    core.info(`ERROR: The following path does not exist: ${reportsPath}, report will not be submitted to testrail`)
  }

  if (fs.statSync(testrailLinkFile).isFile()) {
    const rawFile = fs.readFileSync(testrailLinkFile, 'utf8')
    core.info(`Testrail run available at: ${rawFile.toString()}`)
  }
}