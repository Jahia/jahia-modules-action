import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {readRelease} from './readRelease.js'

const pack = (name: string) =>
  `https://nexus/org/jahia/packages/${name}/8.2.2.1/${name}-8.2.2.1-provisioning.yaml`

test('reads each pack, sorted, and says which pack is missing', async () => {
  const http = fakeHttp({
    [pack('jahia-core-modules')]:
      "- url: 'mvn:org.jahia.modules/tags/8.2.0'\n- url: 'mvn:org.jahia.modules/assets/8.2.0'",
    [pack('jahia-ee-core-modules')]:
      "- url: 'mvn:org.jahia.modules/ldap/4.7.1'\n- url: 'mvn:org.acme/assets/1.0'"
  })
  const release = await readRelease(http, ['https://nexus'], '8.2.2.1')
  expect(release.packs).toEqual({
    'jahia-core-modules': 2,
    'jahia-additional-modules': null,
    'jahia-ee-core-modules': 2
  })
  expect(release.modules.map(module => `${module.groupId}:${module.artifactId}`)).toEqual([
    'org.acme:assets',
    'org.jahia.modules:assets',
    'org.jahia.modules:ldap',
    'org.jahia.modules:tags'
  ])
})

test('is empty for a release with no pack', async () => {
  expect((await readRelease(fakeHttp({}), ['https://nexus'], '9.9.9.9')).modules).toEqual([])
})
