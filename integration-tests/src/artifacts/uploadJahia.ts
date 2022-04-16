import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'
import {add, format} from 'date-fns'

export async function uploadArtifactJahia(
  artifactName: string,
  artifactPath: string,
  retentionDays: number,
  repository: string,
  runId: string,
  runAttempt: string
): Promise<any> {
  const cleanedArtifactName = artifactName
    .replace(/[^a-z0-9+]+/gi, '')
    .toLowerCase()

  const expiryDate = add(new Date(), {days: retentionDays})
  const dstPath = `delete-on-${format(
    expiryDate,
    'YYYY-MM-dd'
  )}_${repository.replace(
    '/',
    '_'
  )}_${cleanedArtifactName}_${runId}_${runAttempt}`
  const dstFilePath = `/temp-artifacts/${dstPath}`
  const dstUrl = `https://qa.jahia.com/artifacts-ci/${dstPath}`

  core.info(`Will be uploading artifact to: ${dstFilePath}`)
  core.info(`Artifacts will be available at: ${dstUrl}`)

  core.notice(
    `Artifacts location (require VPN)::Artifacts have been uploaded to: ${dstUrl}`
  )
}
