import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

export async function runShellCommands(
  commands: Array<string>,
  logfile: string = ''
): Promise<any> {
  for (const cmd of commands) {
    core.info(`Executing: ${cmd}`)
    let stdOut = ''
    let stdErr = ''

    const options: exec.ExecOptions = {}
    options.listeners = {
      stdout: (data: Buffer) => {
        stdOut += data.toString()
      },
      stderr: (data: Buffer) => {
        stdErr += data.toString()
      }
    }
    await exec.exec(cmd, [], {
      ...options,
      silent: false
    })
    core.info(`${stdOut}${stdErr}`)

    if (
      logfile !== '' &&
      process.env.GITHUB_WORKSPACE &&
      process.env.TESTS_PATH
    ) {
      process.env.GITHUB_WORKSPACE

      const filepath = path.join(
        process.env.GITHUB_WORKSPACE,
        process.env.TESTS_PATH,
        logfile
      )
      const logFileStream = fs.createWriteStream(filepath, {flags: 'a+'})
      logFileStream.write(`Executing: ${cmd}`)
      logFileStream.write(stdOut)
      logFileStream.write(stdErr)
      logFileStream.end()
      core.info(`Saved file to: ${filepath}`)
    }
  }
}
