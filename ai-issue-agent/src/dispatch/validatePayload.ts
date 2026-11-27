// Validation of the payload of a dispatched agent session (contract version 1, in the README
// of ai-issue-agent). A dispatcher typed this string, and every output is read as an
// expression later on, so each field is checked against a strict pattern before it leaves.

// A refusal is an Error that carries a name, so the entry point tells it from a defect of
// its own (the package allows no class).
const REFUSAL = 'DispatchPayloadError'
const refusal = (message: string): Error => Object.assign(new Error(message), { name: REFUSAL })
export const isDispatchPayloadError = (error: unknown): error is Error =>
  error instanceof Error && error.name === REFUSAL

export interface DispatchInput {
  payload: string
  prompt: string
  // Owner of the repository that runs the workflow: the origin must belong to it.
  owner: string
  serverUrl: string
}

export type DispatchOutputs = Record<
  | 'runs_on'
  | 'timeout_minutes'
  | 'model'
  | 'issue_url'
  | 'origin_repository'
  | 'origin_number'
  | 'origin_target'
  | 'session_index'
  | 'remaining_seconds'
  | 'guard_run_id'
  | 'cortex_ref'
  | 'claude_code_version'
  | 'debug'
  | 'skip_smoke_tests'
  | 'reuse_claude_code',
  string
>

const fail = (message: string): never => {
  throw refusal(message)
}

// JSON.stringify answers undefined at run time for undefined, whatever its signature says.
const show = (value: unknown): string => {
  const json = JSON.stringify(value) as string | undefined
  return json ?? 'undefined'
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isInteger = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value)

// The default applies to a field that is absent, never to one that is present and null: an
// explicit null is a malformed value, and it is refused like any other.
const pick = (record: Record<string, unknown>, name: string, fallback: unknown): unknown =>
  Object.hasOwn(record, name) ? record[name] : fallback

const LABEL = /^[A-Za-z0-9_.-]{1,64}$/
const REPOSITORY = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/

export const validatePayload = ({
  payload: rawPayload,
  prompt,
  owner,
  serverUrl,
}: DispatchInput): DispatchOutputs => {
  if (prompt.trim() === '') fail('the prompt is empty: a session needs a request')

  let parsed: unknown
  try {
    parsed = JSON.parse(rawPayload)
  } catch (error) {
    return fail(`the payload is not JSON: ${(error as Error).message}`)
  }
  if (!isRecord(parsed)) return fail('the payload must be a JSON object')
  const payload = parsed

  const text = (name: string, pattern: RegExp, fallback: string): string => {
    const value = pick(payload, name, fallback)
    if (typeof value !== 'string' || !pattern.test(value)) {
      return fail(`${name} must be a string matching ${String(pattern)}, got ${show(value)}`)
    }
    return value
  }

  const integer = (name: string, low: number, high: number, fallback: number): number => {
    const value = pick(payload, name, fallback)
    if (!isInteger(value) || value < low || value > high) {
      return fail(
        `${name} must be an integer from ${String(low)} to ${String(high)}, got ${show(value)}`,
      )
    }
    return value
  }

  const flag = (name: string): string => {
    const value = pick(payload, name, false)
    if (typeof value !== 'boolean') return fail(`${name} must be true or false, got ${show(value)}`)
    return String(value)
  }

  integer('version', 1, 1, 1)

  // One runner label, or a list of labels. Labels are plain words: no expression syntax.
  // `default` is the name of the default runner flavour, which `self-hosted` selects.
  let runner = pick(payload, 'runner', 'self-hosted')
  if (runner === 'default') runner = 'self-hosted'
  const labels: unknown[] =
    typeof runner === 'string' ? [runner] : Array.isArray(runner) ? runner : []
  if (
    labels.length < 1 ||
    labels.length > 5 ||
    !labels.every((item) => typeof item === 'string' && LABEL.test(item))
  ) {
    return fail(
      `runner must be a label or a list of up to 5 labels of [A-Za-z0-9_.-], got ${show(runner)}`,
    )
  }
  const runsOn = typeof runner === 'string' ? labels[0] : labels

  const timeout = integer('timeout_minutes', 6, 360, 65)

  const origin = payload.origin
  if (!isRecord(origin)) return fail('origin is required: {repository, number, target}')
  const repository = origin.repository
  if (typeof repository !== 'string' || !REPOSITORY.test(repository)) {
    return fail(`origin.repository must be owner/repo, got ${show(repository)}`)
  }
  // The agent token reaches every repository of the organization: refuse another owner.
  if ((repository.split('/')[0] ?? '').toLowerCase() !== owner.toLowerCase()) {
    return fail(`origin.repository must belong to ${owner}, got ${repository}`)
  }
  const number = origin.number
  if (!isInteger(number) || number < 1) {
    return fail(`origin.number must be a positive integer, got ${show(number)}`)
  }
  const target = pick(origin, 'target', 'issue')
  if (target !== 'issue' && target !== 'pull_request') {
    return fail(`origin.target must be issue or pull_request, got ${show(target)}`)
  }

  const guardRunId = pick(payload, 'guard_run_id', '')
  if (guardRunId !== '' && (!isInteger(guardRunId) || guardRunId < 1)) {
    return fail(`guard_run_id must be a positive integer or absent, got ${show(guardRunId)}`)
  }

  const kind = target === 'pull_request' ? 'pull' : 'issues'
  return {
    runs_on: JSON.stringify(runsOn),
    timeout_minutes: String(timeout),
    model: text('model', /^[A-Za-z0-9._:/-]{0,100}$/, 'opus'),
    issue_url: `${serverUrl}/${repository}/${kind}/${String(number)}`,
    origin_repository: repository,
    origin_number: String(number),
    origin_target: target,
    session_index: String(integer('session_index', 1, 10000, 1)),
    remaining_seconds: String(integer('remaining_seconds', 0, 10 ** 7, timeout * 60)),
    guard_run_id: String(guardRunId),
    cortex_ref: text('cortex_ref', /^[A-Za-z0-9._/-]{1,100}$/, 'main'),
    claude_code_version: text('claude_code_version', /^[A-Za-z0-9._-]{1,30}$/, 'stable'),
    debug: flag('debug'),
    skip_smoke_tests: flag('skip_smoke_tests'),
    reuse_claude_code: flag('reuse_claude_code'),
  }
}

// The table of the job summary is also the decision log of the dispatch: what ran, where,
// for which thread.
export const renderSummary = (outputs: DispatchOutputs, promptLength: number): string => {
  const keys = [
    'runs_on',
    'timeout_minutes',
    'model',
    'issue_url',
    'session_index',
    'remaining_seconds',
    'guard_run_id',
    'cortex_ref',
    'skip_smoke_tests',
    'reuse_claude_code',
  ] as const
  return [
    '### AI agent execution',
    '',
    '| Parameter | Value |',
    '| -- | -- |',
    ...keys.map((key) => `| ${key} | \`${outputs[key]}\` |`),
    `| prompt length | ${String(promptLength)} characters |`,
    '',
  ].join('\n')
}
