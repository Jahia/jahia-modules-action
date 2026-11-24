import {expect, test} from 'vitest'
import {parsePackProvisioning} from './parsePackProvisioning.js'

test('reads the modules of a pack with their start level and type', () => {
  const yaml = [
    'startLevel: 1',
    '- installBundle:',
    "  - url: 'mvn:org.jahia.modules/app-shell/3.3.0'",
    '    startLevel: 85',
    '  - url: "mvn:org.jahia.modules/assets/8.2.0"',
    "  - url: 'js:mvn:org.jahia.modules.javascript/luxe-jahia-demo/1.0.1/tgz'",
    '  autoStart: true'
  ].join('\n')
  expect(parsePackProvisioning(yaml, 'jahia-core-modules')).toEqual([
    {
      groupId: 'org.jahia.modules',
      artifactId: 'app-shell',
      version: '3.3.0',
      pack: 'jahia-core-modules',
      startLevel: 85
    },
    {groupId: 'org.jahia.modules', artifactId: 'assets', version: '8.2.0', pack: 'jahia-core-modules'},
    {
      groupId: 'org.jahia.modules.javascript',
      artifactId: 'luxe-jahia-demo',
      version: '1.0.1',
      pack: 'jahia-core-modules',
      type: 'js'
    }
  ])
})
