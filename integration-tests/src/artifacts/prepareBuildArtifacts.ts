import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'

// Recursively get all folder matching dirName under the path
const getTargetFolders = async (
  scanPath: string,
  targets: Array<string> = [],
  dirName: string = 'target'
) => {
  const files = fs.readdirSync(scanPath)
  for (const f of files) {
    const filePath = path.join(scanPath, f)
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
  // Remove duplicates
  return [...new Set(targets)]
}

export async function prepareBuildArtifact(
  rootProjectFolder: string,
  testsPath: string
): Promise<any> {
  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    const artifactsFolder = path.join(testsPath, 'artifacts')

    if (!fs.existsSync(rootProjectFolder)) {
      core.info(`Folder: ${rootProjectFolder} does not exist`)
      return
    }

    if (!fs.existsSync(artifactsFolder)) {
      core.info(`Folder: ${artifactsFolder} does not exist`)
      return
    }

    // Search for target/ folder
    const folders = await getTargetFolders(rootProjectFolder)

    core.info(
      `Identified the following target folders: ${JSON.stringify(folders)}`
    )

    for (const targetFolder of folders) {
      const files = fs.readdirSync(targetFolder)
      for (const f of files) {
        // Handle .jar for classic MVN modules and .tgz for NPM modules
        if (f.includes('-SNAPSHOT.jar') || f.includes('-SNAPSHOT.tgz')) {
          const srcFile = path.join(targetFolder, f)
          const dstFile = path.join(artifactsFolder, f)
          core.info(`Copying file: ${srcFile} to ${dstFile}`)
          fs.copyFileSync(srcFile, dstFile)
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
  }
}
