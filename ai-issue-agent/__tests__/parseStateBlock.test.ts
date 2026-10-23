import { parseStateBlock } from '../src/state/parseStateBlock'
import { renderStateBlock } from '../src/state/renderStateBlock'
import { sampleState } from './fixtures'

describe('parseStateBlock', () => {
  it('round-trips a rendered state', () => {
    expect(parseStateBlock(renderStateBlock(sampleState()))).toEqual(sampleState())
  })

  it('returns null when no state marker is present', () => {
    expect(parseStateBlock('just a human comment')).toBeNull()
  })

  it('returns null on corrupt JSON', () => {
    expect(parseStateBlock('<!-- cortex-issue-agent-state\n{not json}\n-->')).toBeNull()
  })

  it('returns null when the close marker is missing', () => {
    expect(parseStateBlock('<!-- cortex-issue-agent-state\n{"version":1}')).toBeNull()
  })

  it('returns null on a wrong version or shape', () => {
    expect(
      parseStateBlock('<!-- cortex-issue-agent-state\n{"version":2,"sessions":[]}\n-->'),
    ).toBeNull()
    expect(parseStateBlock('<!-- cortex-issue-agent-state\n{"version":1}\n-->')).toBeNull()
    expect(parseStateBlock('<!-- cortex-issue-agent-state\n"a string"\n-->')).toBeNull()
  })
})
