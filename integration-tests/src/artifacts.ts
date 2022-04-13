import * as core from '@actions/core'
import * as artifact from '@actions/artifact'
import * as fs from 'fs'

export async function downloadArtifact(artifactName: string): Promise<any> {
  const artifactClient = artifact.create()

  const downloadResponse = await artifactClient.downloadArtifact(artifactName)
  core.info(
    `🗄️ The following file was downloaded: ${downloadResponse.artifactName} to ${downloadResponse.downloadPath}`
  )
}

// Recursively get all folder matching dirName under the path
const getTargetFolders = async (
  path: string,
  targets: Array<string> = [],
  dirName: string = 'cypress'
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
  // Search for target/ folder
  const folders = await getTargetFolders(rootPath)
  core.info(JSON.stringify(folders))

  if (!fs.existsSync(`${testsPath}/artifacts/`)) {
    fs.mkdirSync(`${testsPath}/artifacts/`)
  }
}
