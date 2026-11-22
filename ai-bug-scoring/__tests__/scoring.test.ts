import { checkFactors } from '../src/score/checkFactors'
import { evaluateBug } from '../src/score/evaluateBug'
import { renderComment } from '../src/score/renderComment'
import { scoreFactors } from '../src/score/scoreFactors'
import type { Factors } from '../src/types'
import { bug, factors } from './fixtures'

const REF = 'Jahia/example#1'

describe('scoreFactors', () => {
  it('scores the worked example of the documentation at 55', () => {
    const { points } = scoreFactors(factors(), ['customer'])
    expect(points).toBe(55)
  })

  it('caps a crash reported by five customers at three', () => {
    const { points, rows } = scoreFactors(
      factors({ impact: 'unstable', customers: 5, regression: false, cloud: true }),
      ['customer', 'backport'],
    )
    expect(points).toBe(40 + 15 + 4 + 15 + 6 + 3)
    expect(rows).toContainEqual({ name: 'Customers', text: '3', points: 15 })
  })

  it('gives a data loss its points with no bonus', () => {
    const { points } = scoreFactors(factors({ impact: 'data' }), ['customer'])
    expect(points).toBe(40 + 15 + 4 + 5 + 5 + 6)
  })

  it('gates the customer count on the customer label', () => {
    const without = scoreFactors(factors({ customers: 4 }), [])
    expect(without.rows).toContainEqual({ name: 'Customers', text: 'No customer label', points: 0 })
    const withLabel = scoreFactors(factors({ customers: 0 }), ['customer'])
    expect(withLabel.points - without.points).toBe(5)
  })

  it('counts the cloud and regression labels even when the agent missed them', () => {
    const { points } = scoreFactors(factors({ regression: false, cloud: false }), [
      'customer',
      'cloud',
      'regression',
    ])
    expect(points).toBe(20 + 15 + 4 + 5 + 5 + 6 + 3)
  })

  it('takes five points from an older-version-only bug', () => {
    const { points } = scoreFactors(factors({ older_version_only: true }), ['customer'])
    expect(points).toBe(50)
  })
})

describe('checkFactors', () => {
  it('finds no problem in valid factors', () => {
    expect(checkFactors(factors(), REF)).toEqual([])
  })

  it('flags an unknown value', () => {
    expect(checkFactors(factors({ impact: 'blocker' }), REF)).not.toEqual([])
    expect(checkFactors(factors({ reach: 'huge' }), REF)).not.toEqual([])
  })

  it('flags a missing key or a wrong type', () => {
    const missing: Record<string, unknown> = { ...factors() }
    delete missing.why
    expect(checkFactors(missing, REF)).not.toEqual([])
    expect(checkFactors(factors({ customers: true as unknown as number }), REF)).not.toEqual([])
    expect(checkFactors(factors({ customers: '2' as unknown as number }), REF)).not.toEqual([])
  })

  it('flags the factors of another ticket', () => {
    expect(checkFactors(factors({ ref: 'Jahia/example#2' }), REF)).not.toEqual([])
  })

  it('flags a list', () => {
    expect(checkFactors([factors()], REF)).toEqual(['not a JSON object'])
  })

  it('flags a decimal and a negative customers count', () => {
    expect(checkFactors(factors({ customers: 2.5 }), REF).join('; ')).toContain(
      'customers: expected int',
    )
    expect(checkFactors(factors({ customers: -1 }), REF).join('; ')).toContain(
      'customers: -1 is negative',
    )
  })
})

describe('evaluateBug', () => {
  it('skips a bug whose ticket was not fetched', () => {
    const result = evaluateBug(bug(1), new Error('ENOENT'), factors(), {
      marker: '<!-- m -->',
      agent: 'Claude Code',
      runUrl: 'https://run',
      date: '2026-11-20',
    })
    expect(result.outcome).toBe('skipped')
    expect(result.reason).toBe('ticket not fetched')
  })
})

describe('renderComment', () => {
  const render = (over: Partial<Factors> = {}): string => {
    const valid = factors(over)
    const { points, rows } = scoreFactors(valid, ['customer'])
    return renderComment({
      marker: '<!-- m -->',
      points,
      rows,
      factors: valid,
      agent: 'Claude Code',
      runUrl: 'https://run',
      date: '2026-11-20',
    })
  }

  it('opens with the marker and shows the total', () => {
    const body = render()
    expect(body.startsWith('<!-- m -->\n')).toBe(true)
    expect(body).toContain('**🤖 PM score: 55**')
    expect(body).toContain('| **Total** | | **55** |')
    expect(body).toContain('| Impact | Editors blocked | +20 |')
    expect(body).toContain('| Jahia Cloud | No | 0 |')
  })

  it('shows the plain total for a data loss', () => {
    const body = render({ impact: 'data' })
    expect(body).toContain('**🤖 PM score: 75**')
    expect(body).not.toContain('P1')
  })

  it('asks for a check on a low confidence', () => {
    expect(render({ confidence: 'low' })).toContain('please check it')
  })
})
