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

export async function prepareBuildArtifact(
  modulePath: string,
  testsPath: string
): Promise<any> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🛠️ Preparing build artifactsabcd')

    const artifactsFolder = path.join(testsPath, 'artifacts')

    if (!fs.existsSync(modulePath)) {
      core.info(`Folder: ${modulePath} does not exist`)
      return
    }

    if (!fs.existsSync(artifactsFolder)) {
      core.info(`Folder: ${artifactsFolder} does not exist`)
      return
    }

    // Search for target/ folder
    const folders = await getTargetFolders(modulePath)

    core.info(
      `Identified the following target folders: ${JSON.stringify(folders)}`
    )

    for (const targetFolder of folders) {
      const files = fs.readdirSync(targetFolder)
      for (const f of files) {
        if (f.includes('-SNAPSHOT.jar')) {
          core.info(
            `Copying file: ${targetFolder} + '/' + ${f} to ${artifactsFolder}`
          )
          fs.copyFileSync(
            `${targetFolder} + '/' + ${f}`,
            `${artifactsFolder} + '/' + ${f}`
          )
        }
      }
    }

    const files = fs.readdirSync(artifactsFolder)
    if (files.length > 0) {
      core.info(`The following files are present in: ${artifactsFolder}`)
      for (const f of files) {
        core.info(f)
      }
    } else {
      core.info(`Artifacts folder is empty: ${artifactsFolder}`)
    }

    core.endGroup()
  }
}
