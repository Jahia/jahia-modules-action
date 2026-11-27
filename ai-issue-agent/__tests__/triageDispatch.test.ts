import { API_VERSION, dispatchWorkflow } from '../src/triage/dispatch'
import type { DispatchOctokit } from '../src/triage/dispatch'

type Call = Parameters<DispatchOctokit['rest']['actions']['createWorkflowDispatch']>[0]

const RUN = {
  workflow_run_id: 123456789,
  run_url: 'https://api.github.com/repos/Jahia/sandbox/actions/runs/123456789',
  html_url: 'https://github.com/Jahia/sandbox/actions/runs/123456789',
}

const fake = (
  fail?: Error,
  response: { data?: unknown } = { data: RUN },
): { octokit: DispatchOctokit; calls: Call[] } => {
  const calls: Call[] = []
  return {
    calls,
    octokit: {
      rest: {
        actions: {
          createWorkflowDispatch: (parameters) => {
            calls.push(parameters)
            return fail === undefined ? Promise.resolve(response) : Promise.reject(fail)
          },
        },
      },
    },
  }
}

const options = (octokit: DispatchOctokit, repository = 'Jahia/sandbox') => ({
  octokit,
  repository,
  workflow: 'delivery-ai-agent.yml',
  ref: 'main',
  payload: { version: 1, runner: ['self-hosted', 'small'] },
  prompt: 'A request with `backticks`, ${{ expressions }} and "quotes".',
})

describe('dispatchWorkflow', () => {
  it('dispatches the workflow of the repository on its ref', async () => {
    const { octokit, calls } = fake()
    await dispatchWorkflow(options(octokit))
    expect(calls).toHaveLength(1)
    expect(calls[0]).toMatchObject({
      owner: 'Jahia',
      repo: 'sandbox',
      workflow_id: 'delivery-ai-agent.yml',
      ref: 'main',
    })
  })

  it('sends the payload as one JSON string and the prompt untouched', async () => {
    const { octokit, calls } = fake()
    await dispatchWorkflow(options(octokit))
    const inputs = calls[0]?.inputs ?? {}
    expect(typeof inputs.payload).toBe('string')
    expect(JSON.parse(inputs.payload ?? '')).toEqual({
      version: 1,
      runner: ['self-hosted', 'small'],
    })
    expect(inputs.prompt).toBe('A request with `backticks`, ${{ expressions }} and "quotes".')
  })

  it('sends nothing but the two inputs of the execution workflow', async () => {
    const { octokit, calls } = fake()
    await dispatchWorkflow(options(octokit))
    expect(Object.keys(calls[0]?.inputs ?? {}).sort()).toEqual(['payload', 'prompt'])
  })

  it('pins the REST API version that answers with the run', async () => {
    const { octokit, calls } = fake()
    await dispatchWorkflow(options(octokit))
    expect(calls[0]?.headers).toEqual({ 'X-GitHub-Api-Version': API_VERSION })
    expect(API_VERSION).toBe('2026-03-10')
  })

  it('returns the id and the web URL of the dispatched run', async () => {
    const { octokit } = fake()
    await expect(dispatchWorkflow(options(octokit))).resolves.toEqual({
      id: '123456789',
      url: 'https://github.com/Jahia/sandbox/actions/runs/123456789',
    })
  })

  it.each([undefined, null, '', {}, { workflow_run_id: {}, html_url: 7 }])(
    'returns empty fields, and does not throw, on the response body %p',
    async (data) => {
      const { octokit } = fake(undefined, { data })
      await expect(dispatchWorkflow(options(octokit))).resolves.toEqual({ id: '', url: '' })
    },
  )

  it('lets the error of the API through, so the caller falls back to the inline session', async () => {
    const { octokit } = fake(new Error('Not Found'))
    await expect(dispatchWorkflow(options(octokit))).rejects.toThrow('Not Found')
  })

  it.each(['sandbox', '/sandbox', 'Jahia/', ''])(
    'refuses the repository %p before any call',
    async (repository) => {
      const { octokit, calls } = fake()
      await expect(dispatchWorkflow(options(octokit, repository))).rejects.toThrow(
        'not a repository',
      )
      expect(calls).toHaveLength(0)
    },
  )
})
