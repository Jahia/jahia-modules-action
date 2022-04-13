import * as core from '@actions/core'
import * as artifact from '@actions/artifact'
import * as fs from 'fs'
import * as path from 'path'

export async function downloadArtifact(artifactName: string): Promise<any> {
  const artifactClient = artifact.create()

  const downloadResponse = await artifactClient.downloadArtifact(artifactName)
  core.info(
    `🗄️ The following file was downloaded: ${downloadResponse.artifactName} to ${downloadResponse.downloadPath}`
  )
}

// Recursively get all files under the path
const getFiles = async (path: string, scannedFiles: Array<string> = []) => {
  const files = fs.readdirSync(path)
  for (const f of files) {
    const filePath = path + '/' + f
    if (fs.statSync(filePath).isDirectory()) {
      const resultFiles = await getFiles(`${filePath}/`, scannedFiles)
      scannedFiles = [...scannedFiles, ...resultFiles]
    } else if (fs.statSync(filePath).isFile()) {
      if (!scannedFiles.includes(filePath)) {
        scannedFiles.push(filePath)
      }
    }
  }
  return scannedFiles
}

export async function uploadArtifact(
  artifactName: string,
  artifactPath: string
): Promise<any> {
  const artifactClient = artifact.create()

  if (process.env.GITHUB_WORKSPACE && process.env.TESTS_PATH) {
    core.startGroup('🗄️ Uploading artifacts')

    const artifactsFiles = await getFiles(
      path.join(
        process.env.GITHUB_WORKSPACE,
        process.env.TESTS_PATH,
        artifactPath
      )
    )

    core.info('About the upload the following files as artifacts: ')
    for (const f of artifactsFiles) {
      const stats = fs.statSync(f)
      core.info(`File: ${f} - size: ${stats.size} bytes`)
    }

    const uploadResponse = await artifactClient.uploadArtifact(
      artifactName,
      artifactsFiles,
      path.join(process.env.GITHUB_WORKSPACE, process.env.TESTS_PATH),
      {
        continueOnError: true
      }
    )
    core.info(
      `Uploaded: ${uploadResponse.artifactName} for a total size of: ${uploadResponse.size}`
    )
    core.endGroup()
  }
}

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
  rootPath: string,
  testsPath: string
): Promise<any> {
  core.startGroup('🛠️ Preparing build artifacts')
  const artifactFolder = `${testsPath}artifacts/`
  // Search for target/ folder
  const folders = await getTargetFolders(rootPath)
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
