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
    if (fs.statSync(path + '/' + f).isDirectory()) {
      if (f !== dirName) {
        const folders = await getTargetFolders(path + '/' + f, targets)
        targets = [...targets, ...folders]
      } else {
        if (!targets.includes(path + '/' + f)) {
          targets.push(path + '/' + f)
        }
      }
      core.info(`Targets (${path}): ${JSON.stringify(targets)}`)
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
