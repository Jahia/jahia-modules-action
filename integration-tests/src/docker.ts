import * as core from '@actions/core'
import * as exec from '@actions/exec'
import * as cp from 'child_process'

export async function buildDockerTestImage(
  testsPath: string,
  testsContainerBranch: string,
  testsImage: string
): Promise<any> {
  core.startGroup('🛠️ Build test docker container')

  cp.execSync(`docker build -t  ${testsImage} ${testsPath}.`)

  // const runCommands: Array<string> = [
  //   // `git checkout ${testsContainerBranch}`,
  //   `docker build -t ${testsImage} .`,
  //   `docker save -o tests_image.tar ${testsImage}`
  // ]

  // for (const cmd of runCommands) {
  //   core.info(`Executing: ${cmd}`)
  //   let stdOut = ''
  //   let stdErr = ''

  //   const options: exec.ExecOptions = {}
  //   options.listeners = {
  //     stdout: (data: Buffer) => {
  //       stdOut += data.toString()
  //     },
  //     stderr: (data: Buffer) => {
  //       stdErr += data.toString()
  //     }
  //   }
  //   await exec.exec('bash', [`cd ${testsPath}; ${cmd}`], {
  //     ...options,
  //     silent: false
  //   })
  //   core.info(`${stdOut}${stdErr}`)
  // }

  core.endGroup()
}
