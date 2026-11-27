import { validatePayload } from '../dispatch/validatePayload'

// The plan of a dispatch: what the triage decided, turned into the payload and the prompt that the
// execution workflow reads. The plan is pure: it reads nothing and sends nothing, so each rule of
// the hand-off has a test. A decision that the payload validation of the execution would refuse
// never leaves this module, because the plan falls back to the default parameters first.

export type Persona =
  | 'product_manager'
  | 'engineering_manager'
  | 'software_developer'
  | 'devops'
  | 'qa'
  | 'security_engineer'

export interface Origin {
  repo: string
  number: number
  kind: 'issue' | 'pull_request'
  comment_id: number
}

// The fields of a decision of jahia-ai-triage that the dispatch reads.
export interface Decision {
  outcome: 'decision' | 'fallback'
  origin: Origin
  persona: Persona | null
  runner: 'default' | 'small'
  timeout_minutes: number
  execution_repo: string
  model: 'haiku' | 'sonnet' | 'opus'
  prompt_brief: string
  reason: string
  fallback_reason: string | null
}

export interface PlanInput {
  // Null when the triage could not run at all: the plan then holds the default parameters.
  decision: Decision | null
  origin: Origin
  request: { author: string; body: string }
  guardRunId: number
  sessionIndex: number
  remainingSeconds: number
  // The timeout of the guard: the stale-lock rule reclaims a lock older than it plus a margin, so a
  // dispatched session may not run longer than this.
  timeoutJobMinutes: number
  // The model of the inline path today, which a fallback keeps.
  defaultModel: string
  cortexRef: string
  owner: string
  serverUrl: string
}

export interface DispatchPlan {
  payload: Record<string, unknown>
  prompt: string
  // decision: the triage chose. fallback: the triage declined or failed. default: no usable
  // decision reached the plan.
  source: 'decision' | 'fallback' | 'default'
  // Why the plan is not the decision, when it is not.
  note: string
}

const PERSONA_LABEL: Record<Persona, string> = {
  product_manager: 'Product Manager',
  engineering_manager: 'Engineering Manager',
  software_developer: 'Software Developer',
  devops: 'DevOps',
  qa: 'QA',
  security_engineer: 'Security Engineer',
}

// The dispatch ceiling of GitHub is 65 KB for all the inputs, so the request is cut well below it.
const MAX_REQUEST_CHARACTERS = 30000

const MIN_TIMEOUT_MINUTES = 6
const MAX_TIMEOUT_MINUTES = 360

const clamp = (value: number, low: number, high: number): number =>
  Math.min(Math.max(value, low), high)

const requestBlock = (input: PlanInput): string => {
  const { author, body } = input.request
  const cut =
    body.length > MAX_REQUEST_CHARACTERS
      ? `${body.slice(0, MAX_REQUEST_CHARACTERS)}\n\n[the request was cut here]`
      : body
  return `The request, verbatim (${author}, comment ${String(input.origin.comment_id)}):\n\n${cut}`
}

const buildPayload = (
  input: PlanInput,
  parameters: { runner: string | string[]; timeoutMinutes: number; model: string },
): Record<string, unknown> => ({
  version: 1,
  runner: parameters.runner,
  timeout_minutes: clamp(
    Math.min(parameters.timeoutMinutes, input.timeoutJobMinutes),
    MIN_TIMEOUT_MINUTES,
    MAX_TIMEOUT_MINUTES,
  ),
  model: parameters.model,
  origin: {
    repository: input.origin.repo,
    number: input.origin.number,
    target: input.origin.kind,
  },
  session_index: input.sessionIndex,
  remaining_seconds: Number.isFinite(input.remainingSeconds)
    ? Math.max(0, Math.floor(input.remainingSeconds))
    : input.timeoutJobMinutes * 60,
  guard_run_id: input.guardRunId,
  cortex_ref: input.cortexRef,
})

const refusal = (
  input: PlanInput,
  payload: Record<string, unknown>,
  prompt: string,
): string | null => {
  try {
    validatePayload({
      payload: JSON.stringify(payload),
      prompt,
      owner: input.owner,
      serverUrl: input.serverUrl,
    })
    return null
  } catch (error) {
    return error instanceof Error ? error.message : String(error)
  }
}

// Today's parameters and the request, verbatim: what the inline agent would have run.
const defaultPlan = (
  input: PlanInput,
  source: 'fallback' | 'default',
  note: string,
): DispatchPlan => {
  const payload = buildPayload(input, {
    runner: 'self-hosted',
    timeoutMinutes: input.timeoutJobMinutes,
    model: input.defaultModel,
  })
  const prompt = requestBlock(input)
  const refused = refusal(input, payload, prompt)
  if (refused !== null)
    throw new Error(`the default parameters fail the payload validation: ${refused}`)
  return { payload, prompt, source, note }
}

export const planDispatch = (input: PlanInput): DispatchPlan => {
  const { decision } = input
  if (decision === null) return defaultPlan(input, 'default', 'the triage returned nothing usable')
  if (decision.outcome === 'fallback') {
    return defaultPlan(
      input,
      'fallback',
      `the triage fell back: ${decision.fallback_reason ?? 'no reason'}`,
    )
  }

  const payload = buildPayload(input, {
    runner: decision.runner === 'small' ? ['self-hosted', 'small'] : 'self-hosted',
    timeoutMinutes: decision.timeout_minutes,
    model: decision.model,
  })
  const persona =
    decision.persona === null
      ? ''
      : `Persona hint: ${PERSONA_LABEL[decision.persona]}. It is a hint: read the whole thread, and take another profile if the request needs it.\n\n`
  const prompt = `${persona}Brief: ${decision.prompt_brief}\n\n${requestBlock(input)}`

  const refused = refusal(input, payload, prompt)
  if (refused !== null) {
    return defaultPlan(input, 'fallback', `the decision fails the payload validation: ${refused}`)
  }
  return { payload, prompt, source: 'decision', note: '' }
}
