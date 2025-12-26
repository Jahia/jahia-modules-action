import * as core from '@actions/core'
import * as exec from '@actions/exec'
import path from 'path/posix'

import {runShellCommands} from '../utils'

export async function copyRunArtifacts(
  containerName: string,
  desinationPath: string,
  testsFolder: string
): Promise<void> {
  await runShellCommands(
    [`docker cp ${containerName}:/home/jahians/results ${desinationPath}`],
    'artifacts/cypress-artifacts.log',
    {
      ignoreReturnCode: true
    }
  )

  await runShellCommands(
    [`docker stats --all --no-stream`],
    'artifacts/results/cypress-stats.log',
    {
      ignoreReturnCode: true
    }
  )

  await runShellCommands(
    [`docker-compose logs -t --tail="all" `],
    'artifacts/results/all-containers.log',
    {
      cwd: testsFolder,
      ignoreReturnCode: true,
      silent: true
    }
  )

    async function getRunningContainerNames(): Promise<string[]> {
        const output: string = await core.group('List Docker containers', async () => {
            return await exec.getExecOutput('docker', ['ps', '-a', '--format', '{{.Names}}'], {
                ignoreReturnCode: true,
                silent: true
            }).then((r: exec.ExecOutput) => r.stdout ?? '')
        })

        return output
            .split('\n')
            .map(s => s.trim())
            .filter(Boolean)
    }

    const containerNames = await getRunningContainerNames()

    for (const name of containerNames) {
        await runShellCommands(
            [`docker logs ${name}`],
            `artifacts/results/${name}.log`,
            {
                ignoreReturnCode: true,
                silent: true
            }
        )
    }

  await runShellCommands(
    [
      `cp ${path.join(desinationPath, `docker.log`)} ${path.join(
        desinationPath,
        `results/docker.log`
      )}`
    ],
    null,
    {
      ignoreReturnCode: true
    }
  )
}
