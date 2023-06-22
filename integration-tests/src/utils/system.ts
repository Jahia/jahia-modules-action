import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

interface CustomOptions {
  printCmd?: boolean
  loggingMode?: string
}

export async function runShellCommands(
  commands: Array<string>,
  logfile: string | null = null,
  options: exec.ExecOptions & CustomOptions = {}
): Promise<any> {
  for (const cmd of commands) {
    let silent = false
    if (
      options.silent !== undefined ||
      options.silent === true ||
      options.loggingMode === 'silent' ||
      options.loggingMode === 'partial'
    ) {
      silent = true
    }
    if (options.printCmd === undefined || options.printCmd === true) {
      core.info(`Executing: ${cmd} with options: ${JSON.stringify(options)}`)
    } else {
      core.info(
        `Executing a ##OBFUSCATED## command with options: ${JSON.stringify(
          options
        )}`
      )
    }

    let stdOut = ''
    let stdErr = ''

    if (options.loggingMode === 'partial') {
      core.notice(
        `Command output has been silenced, a portion of the logs will be displayed once job is complete`
      )
    }

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
      silent: silent
    })

    if (
      logfile !== null &&
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

      if (options.loggingMode === 'partial') {
        const logs = stdOut.split('\n')
        if (logs.length > 500) {
          logs.slice(0, 250).forEach(line => core.info(line))
          core.notice(
            `...... Partial output displayed, see: ${filepath} for full output ......`
          )
          logs.slice(-250).forEach(line => core.info(line))
        }
      }

      const logFileStream = fs.createWriteStream(filepath, {flags: 'a+'})
      logFileStream.write(`Executing: ${cmd}`)
      logFileStream.write('===== STDOUT =====')
      logFileStream.write(stdOut)
      logFileStream.write('===== STDERR =====')
      logFileStream.write(stdErr)
      logFileStream.end()
      core.info(`Saved command output to: ${filepath}`)
    }
  }
}
