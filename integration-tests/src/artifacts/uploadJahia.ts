import * as core from '@actions/core'
import * as fs from 'fs'
import * as path from 'path'
import {add, format} from 'date-fns'
import {runShellCommands} from '../utils/system'
import * as Rsync from 'rsync'

const runRsync = async (
  artifactPath: string,
  dstFilePath: string
): Promise<any> => {
  const rsync = Rsync.build({})

  rsync
    .shell('ssh')
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

  // const rsync = build({})
  //   .shell('ssh')
  //   .flags('rvz')
  //   .set(
  //     'e',
  //     'ssh -A -o "ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=off -W %h:%p -p 220 jahia-ci@circleci-bastion-prod.jahia.com" -o StrictHostKeyChecking=off'
  //   )
  //   .source(artifactPath)
  //   .destination(`jahia@rqa1.int.jahia.com:${dstFilePath}`)

  // core.info(`About to execute: ${rsync.command()}`)

  const rsyncOut = await runRsync(artifactPath, dstFilePath)
  core.info(JSON.stringify(rsyncOut))

  // const runCommands = [
  //   `rsync -rvz -e \'ssh -A -o "ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=off -W %h:%p -p 220 jahia-ci@circleci-bastion-prod.jahia.com" -o StrictHostKeyChecking=off\' ${artifactPath} jahia@rqa1.int.jahia.com:${dstFilePath}`
  // ]

  // await runShellCommands(runCommands, 'artifacts/artifacts-upload-jahia.log')

  /*
    - uses: webfactory/ssh-agent@v0.5.4
      if: ${{ inputs.destination == 'jahia' }}
      with:
          ssh-private-key: ${{ inputs.ssh-key }}

    - name: rsync files to Jahia
      if: ${{ inputs.destination == 'jahia' }}
      shell: bash
      run: |
        ls -lah
        if ! sh -c "rsync -rvz -e 'ssh -A -o \"ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=off -W %h:%p -p 220 jahia-ci@circleci-bastion-prod.jahia.com\" -o StrictHostKeyChecking=off' ${{ inputs.path }} jahia@rqa1.int.jahia.com:${RSYNC_FOLDER}"
        then
          echo ::set-output name=status::'There was an issue syncing the content.'
          exit 1
        else
          echo ::set-output name=status::'Content synced successfully.'
        fi
*/

  core.notice(`Artifacts (VPN Reqquired) have been uploaded to: ${dstUrl}`)
}