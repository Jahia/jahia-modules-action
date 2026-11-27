// The dispatch call of the execution workflow. `workflow_dispatch` takes its inputs as strings, so
// the payload travels as one JSON string and the prompt as a text, never through a shell.

export interface DispatchOctokit {
  rest: {
    actions: {
      createWorkflowDispatch: (parameters: {
        owner: string
        repo: string
        workflow_id: string
        ref: string
        inputs: Record<string, string>
      }) => Promise<unknown>
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

export const dispatchWorkflow = async (options: DispatchOptions): Promise<void> => {
  const [owner = '', repo = ''] = options.repository.split('/')
  if (owner === '' || repo === '') throw new Error(`not a repository: ${options.repository}`)
  await options.octokit.rest.actions.createWorkflowDispatch({
    owner,
    repo,
    workflow_id: options.workflow,
    ref: options.ref,
    inputs: { payload: JSON.stringify(options.payload), prompt: options.prompt },
  })
}
