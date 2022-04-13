import * as core from '@actions/core'
import * as artifact from '@actions/artifact'
import * as fs from 'fs'
import * as path from 'path'

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
