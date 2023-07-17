import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

interface CustomOptions {
  printCmd?: boolean
  loggingMode?: string
  timeoutMinutes?: number
}

// Adds a timeout mechanism to the exec using AbortController
async function execWithTimeout (execCmd: any, execOptions: any): Promise<any> {
  core.info(`Command starting at: ${JSON.stringify(new Date())}`)
  try {
    await exec.exec(execCmd, [], execOptions)
    core.info(`Command completed at: ${JSON.stringify(new Date())}`)
  } catch (error: any) {
    if (error.name === "AbortError") {
      core.info(`Timeout reached at: ${JSON.stringify(new Date())}. The command was interrupted`)
    } else {
      core.info(`There was an issue processing the command (${error.name}). It failed at: ${JSON.stringify(new Date())}`)
    }
  }
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
    } else {
      core.info(
        `Executing a ##OBFUSCATED## command with options: ${JSON.stringify(
          options
        )}`
      )
    }

    let stdOut = ''
    let stdErr = ''
    let stdDebug = ''

    if (options.loggingMode === 'partial') {
      core.notice(`Command output has been silenced, a portion of the logs will be displayed once job is complete`)
    }

    options.listeners = {
      stdout: (data: Buffer) => {
        stdOut += data.toString()
      },
      stderr: (data: Buffer) => {
        stdErr += data.toString()
      },
      debug: (data: string) => {
        stdDebug += data.toString()
      }      
    }


    // Default timeout is set to a very high value on purpose, in most cases a lower timeout value will be set in startDockerEnvironment
    const defaultTimeout = 360
    core.info(`Timeout for the command is set to ${options.timeoutMinutes === undefined ? defaultTimeout : options.timeoutMinutes}mn`)
    const timeoutDelay = options.timeoutMinutes === undefined ? defaultTimeout*60*1000 : options.timeoutMinutes*60*1000;
    const signal = AbortSignal.timeout(timeoutDelay);

    signal.addEventListener("abort", () => {
      core.info(`Timeout reached at: ${JSON.stringify(new Date())}. Listener event`)
    }, { once: true });

    await execWithTimeout(cmd, {
      ...options,
      silent: silent,
      signal: signal
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
          logs.slice(0, 250).forEach((line) => core.info(line))
          core.notice(`...... Partial output displayed, see: ${filepath} for full output ......`)
          logs.slice(-250).forEach((line) => core.info(line))
        }
      }      
      
      const logFileStream = fs.createWriteStream(filepath, {flags: 'a+'})
      logFileStream.write(`Executing: ${cmd}`)
      logFileStream.write('===== STDOUT =====')
      logFileStream.write(stdOut)
      logFileStream.write('===== STDERR =====')
      logFileStream.write(stdErr)
      logFileStream.write('===== DEBUG =====')
      logFileStream.write(stdDebug)      
      logFileStream.end()
      core.info(`Saved command output to: ${filepath}`)
    }
  }
}
