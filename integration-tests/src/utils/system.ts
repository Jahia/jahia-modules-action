import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as fs from 'fs'
import * as path from 'path'

interface CustomOptions {
  printCmd?: boolean
  loggingMode?: string
  timeoutMinutes?: number
}

// Wrap the Github exec function with a timeout
// Inspired by: https://javascript.plainenglish.io/how-to-add-a-timeout-limit-to-asynchronous-javascript-functions-3676d89c186d
// Default timeout is set to a very high value on purpose, in most cases a lower timeout value will be set in startDockerEnvironment
async function execWithTimeout (execCmd: any, execOptions: any, signal: any): Promise<any> {  
  function abort() {
    core.info(`Timeout reached at: ${JSON.stringify(new Date())}. The command will be interrupted`)
  }
  signal.addEventListener('abort', abort, { once: true });

  try {
    core.info(`Command started at: ${JSON.stringify(new Date())}`)
    await exec.exec(execCmd, [], execOptions)
    core.info(`Command completed at: ${JSON.stringify(new Date())}`)
  } finally {
    signal.removeEventListener('abort', abort);
  }

  // let timeoutHandle: any;
  // const timeoutDelay = timeoutMinutes*60*1000;
  // core.info(`Timeout for the command is set to ${timeoutMinutes}mn, starting at: ${JSON.stringify(new Date())}`)
  // const timeoutPromise = new Promise((_resolve, reject) => {
  //   timeoutHandle = setTimeout(
  //       () => reject(core.info(`Timeout of ${timeoutMinutes}mn reached at: ${JSON.stringify(new Date())}. The command will be interrupted`)),
  //       timeoutDelay // Converts s to ms
  //   );
  // }); 

  // return Promise.race([asyncPromise, timeoutPromise]).then(result => {
  //   core.info(`Execution completed at ${JSON.stringify(new Date())}`)
  //   clearTimeout(timeoutHandle);
  //   return result;
  // })
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

    if (options.loggingMode === 'partial') {
      core.notice(`Command output has been silenced, a portion of the logs will be displayed once job is complete`)
    }

    options.listeners = {
      stdout: (data: Buffer) => {
        stdOut += data.toString()
      },
      stderr: (data: Buffer) => {
        stdErr += data.toString()
      }
    }

    // const execCmd = exec.exec(cmd, [], {
    //   ...options,
    //   silent: silent
    // })
    const ac = new AbortController();
    core.info(`Timeout for the command is set to ${options.timeoutMinutes === undefined ? 360 : options.timeoutMinutes}mn, starting at: ${JSON.stringify(new Date())}`)
    const defaultTimeout = 360
    const timeoutDelay = options.timeoutMinutes === undefined ? defaultTimeout*60*1000 : options.timeoutMinutes*60*1000;
    setTimeout(() => ac.abort(), timeoutDelay);

    await execWithTimeout(cmd, {
      ...options,
      silent: silent
    }, ac.signal)

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
      logFileStream.end()
      core.info(`Saved command output to: ${filepath}`)
    }
  }
}
