import * as core from '@actions/core'
import * as exec from '@actions/exec'

export async function buildDockerTestImage(
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  core.startGroup('🛠️ Build test docker container')

  const runCommands: Array<string> = [
    // `git checkout ${testsContainerBranch}`,
    `docker build -t ${testsImage} .`,
    `docker save -o tests_image.tar ${testsImage}`
  ]

  for (const cmd of runCommands) {
    core.info(`Exceuting: ${cmd}`)
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
    await exec.exec(cmd, [], {...options, silent: true})
    core.info(`${cmd}: ${stdOut}${stdErr}`)
  }

  core.endGroup()
}
