import * as core from '@actions/core'
import { isDispatchPayloadError, renderSummary, validatePayload } from './validatePayload'

// parse-dispatch entry point: validates the payload of a dispatched agent session and exposes
// its fields as step outputs. Deterministic, no model call, no token. The payload and the
// prompt reach this code as action inputs, which the runner passes through the environment
// and never through a script text, so a typed string cannot inject a command.
const run = async (): Promise<void> => {
  const prompt = core.getInput('prompt')
  try {
    const outputs = validatePayload({
      payload: core.getInput('payload'),
      prompt,
      owner: process.env.GITHUB_REPOSITORY_OWNER ?? '',
      serverUrl: process.env.GITHUB_SERVER_URL ?? 'https://github.com',
    })
    for (const [key, value] of Object.entries(outputs)) core.setOutput(key, value)
    await core.summary.addRaw(renderSummary(outputs, prompt.length)).write()
  } catch (error) {
    if (isDispatchPayloadError(error)) {
      core.setFailed(`Invalid dispatch payload: ${error.message}`)
      return
    }
    throw error
  }
}

run().catch((error: unknown) => {
  core.setFailed(error instanceof Error ? error.message : String(error))
})
