import * as core from '@actions/core'
import * as github from '@actions/github'

import {wait} from './wait'

async function run(): Promise<void> {
  try {
    const checkName = core.getInput('check_name')
    const pullRequest = github.context.payload.pull_request
    const commit = core.getInput('commit')
    const summary = core.getInput('summary')
    const head_sha =
      commit || (pullRequest && pullRequest.head.sha) || github.context.sha    

    const token =
      core.getInput('token') ||
      core.getInput('github_token') ||
      process.env.GITHUB_TOKEN;

    if (!token) {
      core.setFailed('❌ A token is required to execute this action')
      return
    }

    core.startGroup(`📘 Display EC2 Metadata`)
    core.info('TODO')
    core.endGroup()

    core.startGroup(`📘 SSH Connection instructions`)

    const conclusion = 'success'

    const createCheckRequest = {
      ...github.context.repo,
      name: checkName,
      head_sha,
      status: 'completed',
      conclusion,
      output: {
        title: 'SSH Connection instructions',
        summary,
        annotations: [{
          path: 'README.md',
          start_line:1,
          end_line:1,
          annotation_level: 'notice',
          message: 'This is the message \n \n #Title Markdown \n \n some more text'
        }]
      }
    }

    core.info(`ℹ️ Creating check`)
    const octokit = github.getOctokit(token)

    await octokit.rest.checks.create(createCheckRequest)
    core.info('TODO')
    core.endGroup()

    const ms: string = core.getInput('milliseconds')
    core.debug(`Waiting ${ms} milliseconds ...`) // debug is only output if you set the secret `ACTIONS_STEP_DEBUG` to true

    core.debug(new Date().toTimeString())
    await wait(parseInt(ms, 10))
    core.debug(new Date().toTimeString())

    core.setOutput('time', new Date().toTimeString())
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
