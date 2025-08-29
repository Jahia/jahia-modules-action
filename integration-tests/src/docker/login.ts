import * as core from '@actions/core'
import * as exec from '@actions/exec'

export interface DockerRegistry {
  registry?: string
  username: string
  password: string
}

// See: https://github.com/docker/login-action/blob/master/src/docker.ts
export async function login(
  username: string,
  password: string,
  registry?: string
): Promise<void> {
  const registryName = registry || 'Docker Hub'
  core.info(`Logging into ${registryName} as ${username}...`)

  if (!username || !password) {
    throw new Error('Username and password required')
  }

  const loginArgs: Array<string> = ['login', '--password-stdin']
  loginArgs.push('--username', username)

  // Add registry if specified (defaults to Docker Hub if omitted)
  if (registry) {
    loginArgs.push(registry)
  }

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
      core.info(`Login to ${registryName} succeeded!`)
    })
}

export async function loginToMultipleRegistries(
  registries: DockerRegistry[]
): Promise<void> {
  for (const registry of registries) {
    await login(registry.username, registry.password, registry.registry)
  }
}
