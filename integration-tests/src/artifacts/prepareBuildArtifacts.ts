import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

// Recursively get all folder matching dirName under the path
const getTargetFolders = async (
  path: string,
  targets: Array<string> = [],
  dirName: string = 'target'
) => {
  const files = fs.readdirSync(path)
  for (const f of files) {
    const filePath = path + '/' + f
    if (fs.statSync(filePath).isDirectory()) {
      if (f !== dirName) {
        const folders = await getTargetFolders(`${filePath}/`, targets)
        targets = [...targets, ...folders]
      } else {
        if (!targets.includes(filePath)) {
          targets.push(filePath)
        }
      }
    }
  }
  return targets
}

export async function prepareBuildArtifact(): Promise<any> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🛠️ Preparing build artifacts')

    const testFolder = path.join(
      process.env.GITHUB_WORKSPACE,
      process.env.TESTS_PATH
    )

    const artifactFolder = `./artifacts/`
    // Search for target/ folder
    const folders = await getTargetFolders(process.env.GITHUB_WORKSPACE)
    core.info(
      `Identified the following target folders: ${JSON.stringify(folders)}`
    )

    if (folders.length > 0 && !fs.existsSync(artifactFolder)) {
      fs.mkdirSync(artifactFolder)
    }

    for (const targetFolder of folders) {
      const files = fs.readdirSync(targetFolder)
      for (const f of files) {
        if (f.includes('-SNAPSHOT.jar')) {
          core.info(
            `Copying file: ${targetFolder} + '/' + ${f} to ${artifactFolder}`
          )
          fs.copyFileSync(
            `${targetFolder} + '/' + ${f}`,
            `${artifactFolder} + '/' + ${f}`
          )
        }
      }
    }

    const files = fs.readdirSync(artifactFolder)
    if (files.length > 0) {
      core.info(`The following files are present in: ${artifactFolder}`)
      for (const f of files) {
        core.info(f)
      }
    } else {
      core.info(`Artifacts folder is empty: ${artifactFolder}`)
    }

    core.endGroup()
  }
}
