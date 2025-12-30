import * as exec from '@actions/exec'
import path from 'path/posix'

import {runShellCommands} from '../utils'

const silent = {silent: true};

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

    await exec.getExecOutput('docker', ['ps', '-a', '--format', '{{.Names}}']).then((r: exec.ExecOutput) => {
        const output = r.stdout ?? "";
        output.split('\n')
            .map(s => s.trim())
            .filter(Boolean).forEach(name => runShellCommands([`docker logs ${name}`], `artifacts/results/${name}.log`, silent))
    })
    await runShellCommands(
        [
            `cp ${path.join(desinationPath, `docker.log`)} ${path.join(
                desinationPath,
                `results/docker.log`
            )}`
        ],
        null,
        silent
    )
}
