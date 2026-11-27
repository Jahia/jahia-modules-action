import {
  isDispatchPayloadError,
  renderSummary,
  validatePayload,
} from '../src/dispatch/validatePayload'
import type { DispatchOutputs } from '../src/dispatch/validatePayload'
import { RUNNER_FLAVOURS } from '../src/runners'

const ORIGIN = { repository: 'Jahia/sandbox', number: 12 }

const run = (
  payload: unknown,
  { prompt = 'Fix the bug', owner = 'Jahia' }: { prompt?: string; owner?: string } = {},
): DispatchOutputs =>
  validatePayload({
    payload: typeof payload === 'string' ? payload : JSON.stringify(payload),
    prompt,
    owner,
    serverUrl: 'https://github.com',
  })

const valid = (overrides: Record<string, unknown> = {}): Record<string, unknown> => ({
  origin: { ...ORIGIN },
  ...overrides,
})

describe('validatePayload, accepted payloads', () => {
  it('takes the defaults for a minimal payload', () => {
    expect(run(valid())).toEqual({
      runs_on: '["self-hosted","default"]',
      timeout_minutes: '65',
      model: 'opus',
      issue_url: 'https://github.com/Jahia/sandbox/issues/12',
      origin_repository: 'Jahia/sandbox',
      origin_number: '12',
      origin_target: 'issue',
      session_index: '1',
      remaining_seconds: String(65 * 60),
      guard_run_id: '',
      cortex_ref: 'main',
      claude_code_version: 'stable',
      debug: 'false',
      skip_smoke_tests: 'false',
      reuse_claude_code: 'false',
    })
  })

  it('builds a pull URL for a pull request target', () => {
    const outputs = run({ origin: { ...ORIGIN, target: 'pull_request' } })
    expect(outputs.issue_url).toBe('https://github.com/Jahia/sandbox/pull/12')
    expect(outputs.origin_target).toBe('pull_request')
  })

  it('takes runs-on from the runner list, for each flavour', () => {
    for (const flavour of RUNNER_FLAVOURS) {
      expect(JSON.parse(run(valid({ runner: flavour.name })).runs_on)).toEqual(flavour.runsOn)
    }
  })

  it('resolves the older spellings of a flavour', () => {
    expect(JSON.parse(run(valid({ runner: 'self-hosted' })).runs_on)).toEqual([
      'self-hosted',
      'default',
    ])
    expect(JSON.parse(run(valid({ runner: ['small', 'self-hosted'] })).runs_on)).toEqual([
      'self-hosted',
      'small',
    ])
  })

  it('defaults the remaining seconds to the timeout', () => {
    expect(run(valid({ timeout_minutes: 30 })).remaining_seconds).toBe(String(30 * 60))
  })

  it('passes explicit fields through', () => {
    const outputs = run(
      valid({
        model: 'sonnet',
        session_index: 3,
        remaining_seconds: 900,
        guard_run_id: 123456,
        cortex_ref: 'feat/x',
        claude_code_version: '2.1.0',
        debug: true,
        skip_smoke_tests: true,
        reuse_claude_code: true,
      }),
    )
    expect(outputs).toMatchObject({
      model: 'sonnet',
      session_index: '3',
      remaining_seconds: '900',
      guard_run_id: '123456',
      cortex_ref: 'feat/x',
      claude_code_version: '2.1.0',
      debug: 'true',
      skip_smoke_tests: 'true',
      reuse_claude_code: 'true',
    })
  })

  it('ignores the case of the owner', () => {
    expect(() => run({ origin: { repository: 'jahia/sandbox', number: 1 } })).not.toThrow()
  })

  it.each([6, 360])('accepts the timeout bound %i', (minutes) => {
    expect(run(valid({ timeout_minutes: minutes })).timeout_minutes).toBe(String(minutes))
  })

  it('accepts a remaining budget of 0', () => {
    expect(run(valid({ remaining_seconds: 0 })).remaining_seconds).toBe('0')
  })
})

describe('validatePayload, refused payloads', () => {
  const refuses = (payload: unknown, fragment: string, options = {}): void => {
    expect(() => run(payload, options)).toThrow(fragment)
  }

  it('refuses an empty or blank prompt', () => {
    refuses(valid(), 'the prompt is empty', { prompt: '' })
    refuses(valid(), 'the prompt is empty', { prompt: '   \n' })
  })

  it('refuses a payload that is not JSON', () => {
    refuses('{not json', 'the payload is not JSON')
  })

  it('refuses a payload that is not an object', () => {
    refuses('[1, 2]', 'must be a JSON object')
    refuses('null', 'must be a JSON object')
  })

  it('refuses an unsupported version', () => {
    refuses(valid({ version: 2 }), 'version must be an integer from 1 to 1')
  })

  it('refuses a timeout outside 6 to 360', () => {
    refuses(valid({ timeout_minutes: 5 }), 'timeout_minutes must be an integer from 6 to 360')
    refuses(valid({ timeout_minutes: 361 }), 'timeout_minutes must be an integer from 6 to 360')
  })

  it('refuses a boolean, a string and a fraction where an integer is due', () => {
    refuses(valid({ timeout_minutes: true }), 'timeout_minutes must be an integer')
    refuses(valid({ session_index: true }), 'session_index must be an integer')
    refuses(valid({ timeout_minutes: '65' }), 'timeout_minutes must be an integer')
    refuses(valid({ timeout_minutes: 65.5 }), 'timeout_minutes must be an integer')
  })

  it('requires an origin object', () => {
    refuses({}, 'origin is required')
    refuses({ origin: 'Jahia/sandbox#1' }, 'origin is required')
    refuses({ origin: ['Jahia/sandbox', 1] }, 'origin is required')
  })

  it('refuses an origin repository that is not owner/repo', () => {
    refuses(
      { origin: { repository: 'sandbox', number: 1 } },
      'origin.repository must be owner/repo',
    )
    refuses(
      { origin: { repository: 'Jahia/sandbox/extra', number: 1 } },
      'origin.repository must be owner/repo',
    )
    refuses({ origin: { number: 1 } }, 'origin.repository must be owner/repo')
  })

  it('refuses an origin repository of another owner', () => {
    refuses({ origin: { repository: 'evil/repo', number: 1 } }, 'must belong to Jahia')
  })

  it.each([0, -1, '1', true, null, 1.5])('refuses the origin number %p', (bad) => {
    refuses({ origin: { repository: 'Jahia/sandbox', number: bad } }, 'origin.number')
  })

  it('refuses an unknown origin target', () => {
    refuses(
      { origin: { ...ORIGIN, target: 'discussion' } },
      'origin.target must be issue or pull_request',
    )
  })

  it.each([
    'ubuntu-latest',
    'ubuntu-slim',
    'ai-triage',
    '${{ secrets.X }}',
    ['self-hosted', 'ubuntu-latest'],
    ['self-hosted'],
    ['ubuntu-latest'],
    [],
    5,
  ])('refuses the runner %p, which is no flavour of the list', (bad) => {
    refuses(valid({ runner: bad }), 'runner must name a flavour of the runner list')
  })

  it.each([0, -3, '7', true])('refuses the guard run id %p', (bad) => {
    refuses(valid({ guard_run_id: bad }), 'guard_run_id must be a positive integer')
  })

  it('refuses unsafe characters in a text field', () => {
    // An output is read as an expression later on: no quote, brace, space or newline gets through.
    refuses(valid({ model: 'opus; rm -rf /' }), 'model must be a string matching')
    refuses(valid({ model: 'a\nb' }), 'model must be a string matching')
    refuses(valid({ model: 'opus\n' }), 'model must be a string matching')
    refuses(valid({ cortex_ref: "main'}" }), 'cortex_ref must be a string matching')
    refuses(valid({ cortex_ref: '' }), 'cortex_ref must be a string matching')
    refuses(valid({ claude_code_version: 'x'.repeat(31) }), 'claude_code_version must be a string')
    refuses(valid({ model: 7 }), 'model must be a string matching')
  })

  it.each(['debug', 'skip_smoke_tests', 'reuse_claude_code'])(
    'requires %s to be a boolean',
    (name) => {
      refuses(valid({ [name]: 'true' }), `${name} must be true or false`)
      refuses(valid({ [name]: 1 }), `${name} must be true or false`)
    },
  )

  it('refuses an explicit null, which is not the same as an absent field', () => {
    refuses(valid({ model: null }), 'model must be a string matching')
    refuses(valid({ runner: null }), 'runner must name a flavour')
    refuses(valid({ timeout_minutes: null }), 'timeout_minutes must be an integer')
    refuses(valid({ debug: null }), 'debug must be true or false')
    refuses(valid({ guard_run_id: null }), 'guard_run_id must be a positive integer')
    refuses({ origin: { ...ORIGIN, target: null } }, 'origin.target must be issue or pull_request')
  })

  it('refuses a negative remaining budget', () => {
    refuses(valid({ remaining_seconds: -1 }), 'remaining_seconds must be an integer')
  })
})

describe('isDispatchPayloadError', () => {
  it('recognizes a refusal, and nothing else', () => {
    let refusal: unknown
    try {
      run('{not json')
    } catch (error) {
      refusal = error
    }
    expect(isDispatchPayloadError(refusal)).toBe(true)
    expect(isDispatchPayloadError(new Error('a defect'))).toBe(false)
    expect(isDispatchPayloadError('the payload is not JSON')).toBe(false)
  })
})

describe('renderSummary', () => {
  it('lists the decision of the dispatch', () => {
    const summary = renderSummary(run(valid()), 11)
    expect(summary).toContain('### AI agent execution')
    expect(summary).toContain('| timeout_minutes | `65` |')
    expect(summary).toContain('| prompt length | 11 characters |')
  })
})
