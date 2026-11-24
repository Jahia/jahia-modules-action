import {expect, test} from 'vitest'
import {renderProvisioning} from './renderProvisioning.js'

const base = {groupId: 'org.jahia.modules', pack: 'jahia-core-modules', mandatory: false}
const modules = [
  {
    ...base,
    artifactId: 'app-shell',
    version: '3.3.0',
    shippedVersion: '3.3.0',
    mandatory: true,
    withheldVersion: '4.0.0',
    startLevel: 85
  },
  {...base, artifactId: 'jcontent', version: '3.8.1', shippedVersion: '3.2.0'},
  {
    ...base,
    groupId: 'org.jahia.modules.javascript',
    artifactId: 'luxe',
    version: '1.1.0',
    shippedVersion: '1.1.0',
    type: 'js' as const
  }
]
const options = {jahiaVersion: '8.2.2.1', storeUrl: 'https://store', generatedAt: '2026-11-24T10:00:00Z'}

test('renders the script of the Store versions', () => {
  expect(renderProvisioning(modules, {...options, versions: 'store'})).toBe(
    [
      '# Jahia 8.2.2.1: the 3 modules it ships, each at the version its module manager offers from the Store.',
      '# 1 of them are newer than shipped. Store: https://store',
      '# Generated on 2026-11-24T10:00:00Z by jahia-modules-action/modules-provisioning.',
      '- installOrUpgradeBundle:',
      "    - url: 'mvn:org.jahia.modules/app-shell/3.3.0'  # mandatory: the module manager does not offer 4.0.0",
      '      startLevel: 85',
      "    - url: 'mvn:org.jahia.modules/jcontent/3.8.1'  # shipped 3.2.0",
      "    - url: 'js:mvn:org.jahia.modules.javascript/luxe/1.1.0/tgz'",
      '  autoStart: true',
      ''
    ].join('\n')
  )
})

test('renders the script of the shipped versions without the Store line', () => {
  const script = renderProvisioning(modules, {...options, versions: 'shipped'})
  expect(script.split('\n')[0]).toBe('# Jahia 8.2.2.1: the 3 modules it ships, each at the version it ships.')
  expect(script).not.toContain('Store:')
})
