import * as core from '@actions/core'
import * as exec from '@actions/exec'

// See: https://github.com/docker/login-action/blob/master/src/docker.ts
export async function login(username: string, password: string): Promise<void> {
  if (!username || !password) {
    throw new Error('Username and password required')
  }

  const loginArgs: Array<string> = ['login', '--password-stdin']
  loginArgs.push('--username', username)

  core.info(`Logging into Docker Hub...`)

  await exec
    .getExecOutput('docker', loginArgs, {
      ignoreReturnCode: true,
      silent: true,
      input: Buffer.from(password)
    })
    .then(res => {
      if (res.stderr.length > 0 && res.exitCode != 0) {
        throw new Error(res.stderr.trim())
      }
      core.info(`Login Succeeded!`)
    })
}
