// Since we cannot call a GitHub action directly from Javascript code, copying over the logic from:
// https://github.com/webfactory/ssh-agent/blob/master/index.js
import * as core from '@actions/core'
import * as os from 'os'
import * as fs from 'fs'
import * as child_process from 'child_process'

export async function setupSSH(privateKey: string): Promise<any> {
  //https://github.com/webfactory/ssh-agent/blob/master/paths.js
  const home = os.userInfo().homedir
  const sshAgent = 'ssh-agent'
  const sshAdd = 'ssh-add'

  const homeSsh = home + '/.ssh'

  core.info(`Adding GitHub.com keys to ${homeSsh}/known_hosts`)
  fs.mkdirSync(homeSsh, {recursive: true})
  fs.appendFileSync(
    `${homeSsh}/known_hosts`,
    '\ngithub.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=\n'
  )
  fs.appendFileSync(
    `${homeSsh}/known_hosts`,
    '\ngithub.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl\n'
  )
  fs.appendFileSync(
    `${homeSsh}/known_hosts`,
    '\ngithub.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==\n'
  )

  core.info(`Starting ssh-agent`)
  const sshAgentArgs: Array<any> = []

  // Extract auth socket path and agent pid and set them as job variables
  child_process
    .execFileSync(sshAgent, sshAgentArgs)
    .toString()
    .split('\n')
    .forEach(function (line) {
      const matches = /^(SSH_AUTH_SOCK|SSH_AGENT_PID)=(.*); export \1/.exec(
        line
      )

      if (matches && matches.length > 0) {
        // This will also set process.env accordingly, so changes take effect for this script
        core.exportVariable(matches[1], matches[2])
        console.log(`${matches[1]}=${matches[2]}`)
      }
    })

  core.info('Adding private key(s) to agent')

  privateKey.split(/(?=-----BEGIN)/).forEach(function (key) {
    child_process.execFileSync(sshAdd, ['-'], {input: key.trim() + '\n'})
  })

  core.info('Key Added')
  child_process.execFileSync(sshAdd, ['-l'], {stdio: 'inherit'})
}
