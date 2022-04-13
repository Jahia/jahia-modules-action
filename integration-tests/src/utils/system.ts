import * as core from '@actions/core'
import * as exec from '@actions/exec'

export async function runShellCommands(commands: Array<string>): Promise<any> {
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
  }
}
