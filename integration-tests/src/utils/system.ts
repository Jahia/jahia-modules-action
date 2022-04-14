import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

interface CustomOptions {
  printCmd?: boolean
}

export async function runShellCommands(
  commands: Array<string>,
  logfile: string | null = null,
  options: exec.ExecOptions & CustomOptions = {}
): Promise<any> {
  for (const cmd of commands) {
    let silent = false
    if (options.silent === undefined || options.silent === true) {
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
    if (silent === false) {
      core.info('===== STDOUT =====')
      core.info(stdOut)
      core.info('===== STDERR =====')
      core.info(stdErr)
    }

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
