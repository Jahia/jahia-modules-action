import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {timeSinceStart, formatDate} from './utils'

import {
  downloadArtifact,
  prepareBuildArtifact,
  uploadArtifact
} from './artifacts'
import {
  buildDockerTestImage,
  copyRunArtifacts,
  executePostrunScript,
  login,
  pullDockerImages,
  startDockerEnvironment
} from './docker'
import {
  setEnvironmentVariables,
  displaySystemInfo,
  installTooling
} from './init'
import {
  publishToTestrail,
  createPagerdutyIncident,
  sendSlackNotification,
  sendResultsToZencrepes
} from './jahia-reporter'

async function run(): Promise<void> {
  try {
    if (!process.env.GITHUB_WORKSPACE) {
      return
    }

    const startTime = new Date()
    core.info(`Started job at: ${formatDate(startTime)}`)

    // Set the various project folders
    const rootProjectFolder = process.env.GITHUB_WORKSPACE
    if (!fs.existsSync(rootProjectFolder))
      core.setFailed(
        `Folder (rootProjectFolder) does not exist: ${rootProjectFolder}`
      )

    const testsFolder = path.join(
      rootProjectFolder,
      core.getInput('tests_path')
    )
    if (!fs.existsSync(testsFolder))
      core.setFailed(`Folder (testsFolder) does not exist: ${testsFolder}`)

    const artifactsFolder = path.join(testsFolder, 'artifacts')
    if (!fs.existsSync(artifactsFolder)) {
      core.info(`📁 Creating folder: ${artifactsFolder}`)
      fs.mkdirSync(artifactsFolder)
    }
    if (!fs.existsSync(artifactsFolder))
      core.setFailed(
        `Folder (artifactsFolder) does not exist: ${artifactsFolder}`
      )

    // Set environment variables from parameters
    await core.group(
      `${timeSinceStart(startTime)} Set Environment variables`,
      async () => {
        await setEnvironmentVariables()
      }
    )
    // await setEnvironmentVariables()

    // Install various tools (such as jahia-reporter) needed for the workflow
    await installTooling()

    // Display important versions and environment variables
    await displaySystemInfo()

    // Docker login
    // await login(
    //   core.getInput('docker_username'),
    //   core.getInput('docker_password')
    // )
    await core.group(
      `${timeSinceStart(startTime)} 🐋 Docker Login`,
      async () => {
        await login(
          core.getInput('docker_username'),
          core.getInput('docker_password')
        )
      }
    )

    // Download the build artifact
    if (core.getInput('should_use_build_artifacts') === 'true') {
      await downloadArtifact('build-artifacts')
    }

    // Prepare the build artifacts to include them in the docker image
    if (core.getInput('should_skip_artifacts') === 'false') {
      await prepareBuildArtifact(rootProjectFolder, testsFolder)
    }

    // Build the test image
    if (core.getInput('should_build_testsimage') === 'true') {
      await buildDockerTestImage(
        core.getInput('tests_path'),
        core.getInput('tests_container_branch'),
        core.getInput('tests_image')
      )
    }

    // Pull the latest version of Jahia and jCustomer and print docker images cache to console
    await pullDockerImages(
      core.getInput('jahia_image'),
      core.getInput('jcustomer_image')
    )

    // Spin-up the containers
    await startDockerEnvironment(
      testsFolder,
      core.getInput('ci_startup_script'),
      core.getInput('docker_compose_file')
    )

    // Export containers artifacts (reports, secreenshots, videos)
    await copyRunArtifacts(
      core.getInput('tests_container_name'),
      artifactsFolder,
      testsFolder
    )

    // Spin-up the containers
    await executePostrunScript(testsFolder, core.getInput('ci_startup_script'))

    // upload the artifacts
    await uploadArtifact(
      core.getInput('artifact_name'),
      artifactsFolder,
      Number(core.getInput('artifact_retention'))
    )

    // Publish results to testrail
    if (
      core.getInput('should_skip_testrail') === 'false' ||
      // core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
      core.getInput('primary_release_branch') === 'TECH-533_ts_action'
    ) {
      await publishToTestrail(testsFolder, {
        testrailUsername: core.getInput('testrail_username'),
        testrailPassword: core.getInput('testrail_password'),
        testrailProject: core.getInput('testrail_project'),
        testrailMilestone: core.getInput('testrail_milestone')
      })
    }

    // Create incident in PagerDuty
    if (
      process.env.CURRENT_BRANCH === 'master' ||
      process.env.CURRENT_BRANCH === 'main' ||
      // core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
      core.getInput('primary_release_branch') === 'TECH-533_ts_action'
    ) {
      await createPagerdutyIncident(testsFolder, {
        service: core.getInput('module_id'),
        pdApiKey: core.getInput('incident_pagerduty_api_key'),
        pdReporterEmail: core.getInput('incident_pagerduty_reporter_email'),
        pdReporterId: core.getInput('incident_pagerduty_reporter_id'),
        googleSpreadsheetId: core.getInput('incident_google_spreadsheet_id'),
        googleClientEmail: core.getInput('incident_google_client_email'),
        googleApiKey: core.getInput('incident_google_api_key_base64')
      })
    }

    // Send notifications to slack
    if (
      core.getInput('should_skip_notifications') === 'false' ||
      // core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
      core.getInput('primary_release_branch') === 'TECH-533_ts_action'
    ) {
      await sendSlackNotification(testsFolder, {
        channelId: core.getInput('slack_channel_id_notifications'),
        channelAllId: core.getInput('slack_channel_id_notifications_all'),
        token: core.getInput('slack_client_token')
      })
    }

    // Send results to zencrepes
    if (
      core.getInput('should_skip_zencrepes') === 'false' ||
      // core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
      core.getInput('primary_release_branch') === 'TECH-533_ts_action'
    ) {
      await sendResultsToZencrepes(testsFolder, {
        service: core.getInput('module_id'),
        webhookSecret: core.getInput('zencrepes_secret')
      })
    }

    core.info(`Completed job at: ${formatDate(new Date())}`)

    //Finally, analyze the results
    if (!fs.existsSync(path.join(artifactsFolder, 'results/test_success'))) {
      core.setFailed(
        `Could not locate file ${path.join(
          artifactsFolder,
          'results/test_success'
        )}, run has FAILED`
      )
    } else {
      core.info(
        `File ${path.join(
          artifactsFolder,
          'results/test_success'
        )} is present, run is SUCCESSFUL`
      )
    }
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
