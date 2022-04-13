import * as core from '@actions/core'
import * as artifact from '@actions/artifact'

export async function download(artifactName: string): Promise<any> {
  const artifactClient = artifact.create()

  const downloadResponse = await artifactClient.downloadArtifact(artifactName)
  core.startGroup('🛠️ Download build artifact')
  core.info(
    `The following file was downloaded: ${downloadResponse.artifactName} to ${downloadResponse.downloadPath}`
  )
  core.endGroup()
}
