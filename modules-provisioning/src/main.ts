import {mkdir, writeFile} from 'node:fs/promises'
import {dirname, resolve} from 'node:path'
import {info, setFailed, setOutput, setSecret} from '@actions/core'
import {createHttp} from './http/createHttp.js'
import {readInputs} from './readInputs.js'
import {run} from './run.js'

try {
  const inputs = readInputs()
  if (inputs.nexusPassword) setSecret(inputs.nexusPassword)
  const outputs = await run(inputs, {
    http: createHttp({fetch, username: inputs.nexusUsername, password: inputs.nexusPassword}),
    writeFile: async (path, content) => {
      await mkdir(dirname(resolve(path)), {recursive: true})
      await writeFile(path, content, 'utf8')
    },
    now: () => new Date(),
    log: info
  })
  setOutput('provisioning_path', outputs.provisioningPath)
  setOutput('matrix_path', outputs.matrixPath)
  setOutput('modules', outputs.modules)
  setOutput('upgraded', outputs.upgraded)
} catch (error) {
  setFailed(error instanceof Error ? error.message : String(error))
}
