import * as core from '@actions/core'
import {DefaultArtifactClient} from '@actions/artifact'

export async function downloadArtifact(artifactName: string): Promise<any> {
  const artifactClient = new DefaultArtifactClient()  

  // Get artifact name
  const artifact = await artifactClient.getArtifact(artifactName)
  const downloadResponse = await artifactClient.downloadArtifact(artifact.artifact.id)

  core.info(
    `🗄️ The following file was downloaded: ${artifact.artifact.name} to ${downloadResponse.downloadPath}`
  )
}
