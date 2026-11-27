// The dispatch call of the execution workflow. `workflow_dispatch` takes its inputs as strings, so
// the payload travels as one JSON string and the prompt as a text, never through a shell.

// REST API version 2026-03-10 answers 200 with the run it started, where 2022-11-28, the version a
// request without the header gets, answers 204 with no body and logs a deprecation warning.
export const API_VERSION = '2026-03-10'

export interface DispatchOctokit {
  rest: {
    actions: {
      createWorkflowDispatch: (parameters: {
        owner: string
        repo: string
        workflow_id: string
        ref: string
        inputs: Record<string, string>
        headers: Record<string, string>
      }) => Promise<{ data?: unknown }>
    }
  }
}

export interface DispatchOptions {
  octokit: DispatchOctokit
  repository: string
  workflow: string
  ref: string
  payload: Record<string, unknown>
  prompt: string
}

// The run that the dispatch started. A field is empty when the response does not carry it, which
// never fails the dispatch: the run started all the same.
export interface DispatchedRun {
  id: string
  url: string
}

const readRun = (data: unknown): DispatchedRun => {
  const body = typeof data === 'object' && data !== null ? (data as Record<string, unknown>) : {}
  const id = body.workflow_run_id
  const url = body.html_url
  return {
    id: typeof id === 'number' || typeof id === 'string' ? String(id) : '',
    url: typeof url === 'string' ? url : '',
  }
}

export const dispatchWorkflow = async (options: DispatchOptions): Promise<DispatchedRun> => {
  const [owner = '', repo = ''] = options.repository.split('/')
  if (owner === '' || repo === '') throw new Error(`not a repository: ${options.repository}`)
  const response = await options.octokit.rest.actions.createWorkflowDispatch({
    owner,
    repo,
    workflow_id: options.workflow,
    ref: options.ref,
    inputs: { payload: JSON.stringify(options.payload), prompt: options.prompt },
    headers: { 'X-GitHub-Api-Version': API_VERSION },
  })
  return readRun(response.data)
}
