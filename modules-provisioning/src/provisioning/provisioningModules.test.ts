import {expect, test} from 'vitest'
import {provisioningModules} from './provisioningModules.js'

const shipped = [
  'jcontent=3.2.0',
  'app-shell=3.3.0',
  'tags=8.2.0',
  'dx-base-demo=2.4.0',
  'default=8.8.0'
].map(entry => {
  const [artifactId = '', version = ''] = entry.split('=')
  return {groupId: 'org.jahia.modules', artifactId, version, pack: 'jahia-core-modules'}
})
const offers = {
  'org.jahia.modules:jcontent': '3.8.1',
  'org.jahia.modules:app-shell': '4.0.0',
  'org.jahia.modules:tags': '8.2.0',
  'org.jahia.modules:dx-base-demo': '2.2.0'
}
const mandatory = new Set(['app-shell', 'default'])

test('takes the offer of the Store as the page of the module manager does', () => {
  const modules = provisioningModules(shipped, offers, mandatory, 'store')
  expect(
    modules.map(({artifactId, version, shippedVersion, mandatory, withheldVersion}) => ({
      artifactId,
      version,
      shippedVersion,
      mandatory,
      withheldVersion
    }))
  ).toEqual([
    {
      artifactId: 'jcontent',
      version: '3.8.1',
      shippedVersion: '3.2.0',
      mandatory: false,
      withheldVersion: undefined
    },
    {
      artifactId: 'app-shell',
      version: '3.3.0',
      shippedVersion: '3.3.0',
      mandatory: true,
      withheldVersion: '4.0.0'
    },
    {
      artifactId: 'tags',
      version: '8.2.0',
      shippedVersion: '8.2.0',
      mandatory: false,
      withheldVersion: undefined
    },
    {
      artifactId: 'dx-base-demo',
      version: '2.4.0',
      shippedVersion: '2.4.0',
      mandatory: false,
      withheldVersion: undefined
    },
    {
      artifactId: 'default',
      version: '8.8.0',
      shippedVersion: '8.8.0',
      mandatory: true,
      withheldVersion: undefined
    }
  ])
})

test('keeps every shipped version in shipped mode', () => {
  const modules = provisioningModules(shipped, offers, mandatory, 'shipped')
  expect(modules.every(module => module.version === module.shippedVersion && !module.withheldVersion)).toBe(
    true
  )
})
