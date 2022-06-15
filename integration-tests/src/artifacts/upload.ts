import * as core from '@actions/core'
import * as artifact from '@actions/artifact'
import * as fs from 'fs'
import * as path from 'path'

import {cleanArtifactName} from '../utils'

// Recursively get all files under the path
const getFiles = async (
  currentPath: string,
  scannedFiles: Array<string> = []
) => {
  const files = fs.readdirSync(currentPath)
  for (const f of files) {
    const filePath = path.join(currentPath, f)
    if (fs.statSync(filePath).isDirectory()) {
      const resultFiles = await getFiles(filePath, scannedFiles)
      scannedFiles = [...scannedFiles, ...resultFiles]
    } else if (fs.statSync(filePath).isFile()) {
      if (!scannedFiles.includes(filePath)) {
        scannedFiles.push(filePath)
      }
    }
  }
  // Remove duplicates
  return [...new Set(scannedFiles)]
}

export async function uploadArtifact(
  artifactName: string,
  artifactPath: string,
  retentionDays: number
): Promise<any> {
  const cleanedArtifactName = cleanArtifactName(artifactName)
  const artifactClient = artifact.create()
  const artifactsFiles = await getFiles(artifactPath)

  core.info('About the upload the following files as artifacts: ')
  for (const f of artifactsFiles) {
    const stats = fs.statSync(f)
    core.info(`File: ${f} - size: ${stats.size} bytes`)
  }

  const uploadResponse = await artifactClient.uploadArtifact(
    cleanedArtifactName,
    artifactsFiles,
    artifactPath,
    {
      continueOnError: true,
      retentionDays: retentionDays
    }
  )
  core.info(
    `Uploaded: ${uploadResponse.artifactName} for a total size of: ${uploadResponse.size}`
  )
}
