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
    if (options.silent !== undefined || options.silent === true || options.loggingMode === 'silent' || options.loggingMode === 'partial') {
      silent = true
    }
    if (options.printCmd === undefined || options.printCmd === true) {
      core.info(`Executing: ${cmd} with options: ${JSON.stringify(options)}`)
      core.info(`Logging mode: ${JSON.stringify(silent)}`)
    } else {
      core.info(
        `Executing a ##OBFUSCATED## command with options: ${JSON.stringify(
          options
        )}`
      )
    }
    let stdOut = ''
    let stdErr = ''

    // If logging partial, only display the first [maxLogLines] lines
    let logLines = 0;
    let maxLogLines = 10

    options.listeners = {
      stdout: (data: Buffer) => {
        stdOut += data.toString()
        core.info(`Logging via stdout ${logLines} / ${maxLogLines}`)
        if (options.loggingMode === 'partial' && logLines < maxLogLines) {
          core.info(data.toString())
          logLines++
        } else if (options.loggingMode === 'partial') {
          // Using process.stdout since info appends new line
          process.stdout.write('.')
          logLines++
        }
      },
      stderr: (data: Buffer) => {
        stdErr += data.toString()
        if (options.loggingMode === 'partial') {
          core.info(`ERR: ${data.toString()}`)
        }
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
