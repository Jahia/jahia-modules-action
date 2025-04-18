import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

import {timeSinceStart, formatDate} from './utils'

import {
  downloadArtifact,
  prepareBuildArtifact,
  uploadArtifact,
  uploadArtifactJahia,
  listArtifacts
} from './artifacts'
import {
  buildDockerTestImage,
  copyRunArtifacts,
  executePostrunScript,
  login,
  pullDockerImages,
  startDockerEnvironment,
  stopDockerEnvironment
} from './docker'
import {
  setEnvironmentVariables,
  displaySystemInfo,
  installTooling,
  setupSSH
} from './init'
import {
  publishToTestrail,
  createPagerdutyIncident,
  sendSlackNotification,
  sendResultsToZencrepes,
  showTestsSummary,
  prepareTestrailMetadata
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

    // Install various tools (such as jahia-reporter) needed for the workflow
    await core.group(
      `${timeSinceStart(startTime)} 🛠️ Install runtime tooling`,
      async () => {
        await installTooling()
      }
    )

    // Configuring SSH on the host
    if (core.getInput('bastion_ssh_private_key') !== '') {
      await core.group(
        `${timeSinceStart(startTime)} 🛠️ Configure SSH Agent with private key`,
        async () => {
          await setupSSH(core.getInput('bastion_ssh_private_key'))
        }
      )
    }

    // Display important versions and environment variables
    await core.group(
      `${timeSinceStart(
        startTime
      )} 🛠️ Displaying important environment variables and system info`,
      async () => {
        await displaySystemInfo()
      }
    )

    // Docker login
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
    await core.group(
      `${timeSinceStart(startTime)} 🛠️ Download previous build artifact`,
      async () => {
        const artifacts = await listArtifacts()
        const allowedArtifacts = [
          core.getInput('build_artifacts'),
          core.getInput('build_artifacts_tests')
        ]
        for (const artifact of artifacts.filter(artifact =>
          allowedArtifacts.includes(artifact.name)
        )) {
          await downloadArtifact(artifact.name)
        }
      }
    )

    // Prepare the build artifacts to include them in the docker image
    if (core.getInput('should_skip_artifacts') === 'false') {
      await core.group(
        `${timeSinceStart(startTime)} 🛠️ Preparing build artifacts`,
        async () => {
          await prepareBuildArtifact(rootProjectFolder, testsFolder)
        }
      )
    }

    // Build the test image
    if (core.getInput('should_build_testsimage') === 'true') {
      await core.group(
        `${timeSinceStart(startTime)} 🐋 Build test docker container`,
        async () => {
          await buildDockerTestImage(
            testsFolder,
            core.getInput('ci_build_script'),
            core.getInput('tests_container_branch'),
            core.getInput('tests_image')
          )
        }
      )
    }

    // Pull the latest version of Jahia and jCustomer and print docker images cache to console
    await core.group(
      `${timeSinceStart(
        startTime
      )} 🐋 Pull the latest version of Jahia and jCustomer and print docker images cache to console`,
      async () => {
        await pullDockerImages(
          core.getInput('jahia_image'),
          core.getInput('jcustomer_image')
        )
      }
    )

    // Spin-up the containers
    await core.group(
      `${timeSinceStart(
        startTime
      )} 🐋 Starting the Docker environment (will timeout after: ${core.getInput(
        'timeout_minutes'
      )}mn)`,
      async () => {
        await startDockerEnvironment(
          testsFolder,
          core.getInput('ci_startup_script'),
          core.getInput('docker_compose_file'),
          core.getInput('logging_mode'),
          parseInt(core.getInput('timeout_minutes'))
        )
      }
    )

    // Export containers artifacts (reports, secreenshots, videos)
    await core.group(
      `${timeSinceStart(
        startTime
      )} 🐋 Export containers artifacts (reports, secreenshots, videos, logs) `,
      async () => {
        await copyRunArtifacts(
          core.getInput('tests_container_name'),
          artifactsFolder,
          testsFolder
        )
      }
    )

    // Execute post-run script
    await core.group(
      `${timeSinceStart(startTime)} 🐋 Execute Postrun script`,
      async () => {
        await executePostrunScript(
          testsFolder,
          core.getInput('ci_postrun_script')
        )
      }
    )

    // Shut down the containers and clean system
    await core.group(
      `${timeSinceStart(startTime)} 🐋 Stopping the Docker environment`,
      async () => {
        await stopDockerEnvironment(testsFolder, core.getInput('logging_mode'))
      }
    )

    // Display a short "console" report directly in the run output
    await showTestsSummary(
      path.join(testsFolder, core.getInput('tests_report_path')),
      core.getInput('tests_report_type')
    )

    // Publish results to testrail
    // Publish to testrail - into separate project
    if (
      core.getInput('should_skip_testrail') === 'false' ||
      core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
    ) {
      await core.group(
        `${timeSinceStart(
          startTime
        )} 🛠️ Publishing results to Testrail project: ${core.getInput(
          'testrail_project'
        )}`,
        async () => {
          await prepareTestrailMetadata(
            testsFolder,
            core.getInput('testrail_platformdata')
          )

          await publishToTestrail(
            testsFolder,
            core.getInput('tests_report_path'),
            core.getInput('tests_report_type'),
            {
              testrailUsername: core.getInput('testrail_username'),
              testrailPassword: core.getInput('testrail_password'),
              testrailParentSection: '',
              testrailProject: core.getInput('testrail_project'),
              testrailMilestone: core.getInput('testrail_milestone')
            }
          )
        }
      )
    }

    // Publish to testrail into Jahia-CI project
    if (
      core.getInput('should_skip_testrail') === 'false' ||
      core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
    ) {
      await core.group(
        `${timeSinceStart(
          startTime
        )} 🛠️ Publishing results to Testrail project: Jahia-CI}`,
        async () => {
          await prepareTestrailMetadata(
            testsFolder,
            core.getInput('testrail_platformdata')
          )

          await publishToTestrail(
            testsFolder,
            core.getInput('tests_report_path'),
            core.getInput('tests_report_type'),
            {
              testrailUsername: core.getInput('testrail_username'),
              testrailPassword: core.getInput('testrail_password'),
              testrailParentSection: core.getInput('testrail_project'),
              testrailProject: 'JahiaCI',
              testrailMilestone: core.getInput('testrail_milestone')
            }
          )
        }
      )
    }

    // Create incident in PagerDuty
    if (
      core.getInput('should_skip_pagerduty') === 'false' &&
      process.env.CURRENT_BRANCH !== undefined &&
      ['master', 'main', core.getInput('primary_release_branch')].includes(
        process.env.CURRENT_BRANCH
      )
    ) {
      await core.group(
        `${timeSinceStart(
          startTime
        )} 🛠️ Creating incident in Pagerduty (if applicable)`,
        async () => {
          await createPagerdutyIncident(
            path.join(testsFolder, core.getInput('tests_report_path')),
            core.getInput('tests_report_type'),
            {
              service:
                core.getInput('incident_service') || core.getInput('module_id'),
              pdApiKey: core.getInput('incident_pagerduty_api_key'),
              pdReporterEmail: core.getInput(
                'incident_pagerduty_reporter_email'
              ),
              pdReporterId: core.getInput('incident_pagerduty_reporter_id'),
              googleSpreadsheetId: core.getInput(
                'incident_google_spreadsheet_id'
              ),
              googleClientEmail: core.getInput('incident_google_client_email'),
              googleApiKey: core.getInput('incident_google_api_key_base64')
            }
          )
        }
      )
    }

    // Upload the artifacts to GitHub infrastructure
    if (core.getInput('github_artifact_enable') === 'true') {
      await core.group(
        `${timeSinceStart(
          startTime
        )} 🗄️ Uploading artifacts to GitHub infrastructure`,
        async () => {
          await uploadArtifact(
            core.getInput('github_artifact_name'),
            artifactsFolder,
            Number(core.getInput('github_artifact_retention'))
          )
        }
      )
    }

    // Upload artifacts to Jahia infrastructure
    if (core.getInput('jahia_artifact_enable') === 'true') {
      await core.group(
        `${timeSinceStart(
          startTime
        )} 🗄️ Uploading tests artifacts to Jahia servers`,
        async () => {
          if (
            process.env.GITHUB_REPOSITORY !== undefined &&
            process.env.GITHUB_RUN_ID !== undefined &&
            process.env.GITHUB_RUN_ATTEMPT !== undefined
          ) {
            await uploadArtifactJahia(
              core.getInput('jahia_artifact_name'),
              artifactsFolder,
              Number(core.getInput('jahia_artifact_retention')),
              process.env.GITHUB_REPOSITORY,
              process.env.GITHUB_RUN_ID,
              process.env.GITHUB_RUN_ATTEMPT
            )
          }
        }
      )
    }

    // Send notifications to slack
    if (
      core.getInput('should_skip_notifications') === 'false' ||
      core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
    ) {
      await core.group(
        `${timeSinceStart(startTime)} 🛠️ Send notification to Slack`,
        async () => {
          await sendSlackNotification(
            path.join(testsFolder, core.getInput('tests_report_path')),
            core.getInput('tests_report_type'),
            {
              channelId: core.getInput('slack_channel_id_notifications'),
              channelAllId: core.getInput('slack_channel_id_notifications_all'),
              token: core.getInput('slack_client_token')
            }
          )
        }
      )
    }

    // Send results to zencrepes
    if (
      core.getInput('should_skip_zencrepes') === 'false' ||
      core.getInput('primary_release_branch') === process.env.CURRENT_BRANCH
    ) {
      await core.group(
        `${timeSinceStart(startTime)} 🛠️ Send results to ZenCrepes`,
        async () => {
          await sendResultsToZencrepes(
            testsFolder,
            core.getInput('tests_report_path'),
            core.getInput('tests_report_type'),
            {
              service: core.getInput('module_id'),
              webhookSecret: core.getInput('zencrepes_secret')
            }
          )
        }
      )
    }

    core.info(`Completed job at: ${formatDate(new Date())}`)

    //Finally, analyze the results
    if (!fs.existsSync(path.join(artifactsFolder, 'results/test_success'))) {
      core.setFailed(
        `Run has FAILED, could not locate file ${path.join(
          artifactsFolder,
          'results/test_success'
        )}`
      )
    } else {
      core.info(
        `Run is SUCCESSFUL, could locate file ${path.join(
          artifactsFolder,
          'results/test_success'
        )}`
      )
    }
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
