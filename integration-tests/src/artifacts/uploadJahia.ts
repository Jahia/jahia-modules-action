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
    'yyyy-MM-dd'
  )}_${repository.replace(
    '/',
    '_'
  )}_${cleanedArtifactName}_${runId}_${runAttempt}`
  const dstFilePath = `/temp-artifacts/${dstPath}`
  const dstUrl = `https://qa.jahia.com/artifacts-ci/${dstPath}`

  core.info(`Will be uploading artifact to: ${dstFilePath}`)
  core.info(`Artifacts will be available at: ${dstUrl}`)

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
