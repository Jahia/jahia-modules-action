import { parseProjectUrl } from '../src/hygiene/parseProjectUrl'
import { pickOption } from '../src/hygiene/pickOption'

describe('parseProjectUrl', () => {
  it('parses an organization project URL, views suffix included', () => {
    expect(parseProjectUrl('https://github.com/orgs/Jahia/projects/50/views/3')).toEqual({
      org: 'Jahia',
      number: 50,
    })
  })

  it('rejects anything that is not an organization project URL', () => {
    expect(() => parseProjectUrl('https://github.com/Jahia/sandbox/projects/1')).toThrow(
      'not an organization project URL',
    )
  })
})

describe('pickOption', () => {
  const options = [
    { id: 'o1', name: 'Now' },
    { id: 'o2', name: 'In Progress ' },
    { id: 'o3', name: '🐐 GOAT' },
  ]

  it('matches exactly', () => {
    expect(pickOption(options, 'Now')).toBe('o1')
  })

  it('matches emoji names', () => {
    expect(pickOption(options, '🐐 GOAT')).toBe('o3')
  })

  it('tolerates case and padding differences on either side', () => {
    expect(pickOption(options, 'in progress')).toBe('o2')
  })

  it('returns null for an unknown option', () => {
    expect(pickOption(options, 'Later')).toBeNull()
  })
})
