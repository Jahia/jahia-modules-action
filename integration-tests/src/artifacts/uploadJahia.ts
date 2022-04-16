import * as core from '@actions/core'
import {add, format} from 'date-fns'
import * as Rsync from 'rsync'

const runRsync = async (
  artifactPath: string,
  dstFilePath: string
): Promise<any> => {
  const rsync = Rsync.build({})

  rsync
    .flags('rvz')
    .set(
      'e',
      'ssh -A -o "ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=off -W %h:%p -p 220 jahia-ci@circleci-bastion-prod.jahia.com" -o StrictHostKeyChecking=off'
    )
    .source(artifactPath)
    .destination(`jahia@rqa1.int.jahia.com:${dstFilePath}`)

  core.info(`About to execute: ${rsync.command()}`)

  return new Promise((resolve, reject) => {
    try {
      let logData = ''
      rsync.execute(
        (error, code, cmd) => {
          resolve({error, code, cmd, data: logData})
        },
        data => {
          logData += data
        },
        err => {
          logData += err
        }
      )
    } catch (error) {
      reject(error)
    }
  })
}

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
    'yyyy-MM-dd'
  )}_${repository.replace(
    '/',
    '_'
  )}_${cleanedArtifactName}_${runId}_${runAttempt}`
  const dstFilePath = `/temp-artifacts/${dstPath}`
  const dstUrl = `https://qa.jahia.com/artifacts-ci/${dstPath}`

  core.info(`Will be uploading artifact to: ${dstFilePath}`)
  core.info(`Artifacts will be available at: ${dstUrl}`)

  const rsyncOut = await runRsync(artifactPath, dstFilePath)
  core.info(`Submission error (if present): ${JSON.stringify(rsyncOut.error)}`)
  core.info(`cmd: ${JSON.stringify(rsyncOut.cmd)}`)
  core.info(`Submission data (if present): ${JSON.stringify(rsyncOut.data)}`)

  core.notice(`Artifacts (VPN Required) have been uploaded to: ${dstUrl}`)
}
