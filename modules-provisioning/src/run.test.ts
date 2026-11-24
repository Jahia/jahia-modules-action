import {gzipSync} from 'node:zlib'
import {expect, test} from 'vitest'
import {PUBLIC_REPOSITORY, STORE_PROXY} from './constants.js'
import {run} from './run.js'
import {fakeHttp} from './testing/fakeHttp.js'
import {jarOf} from './testing/jarOf.js'
import {tarOf} from './testing/tarOf.js'
import type {Inputs} from './types.js'

const STORE = 'https://store/site'
const inputs: Inputs = {
  jahiaVersion: '8.2.2.1',
  versions: 'store',
  storeUrl: STORE,
  nexusUsername: '',
  nexusPassword: '',
  provisioningPath: 'out/modules.yml',
  matrixPath: 'out/matrix.json'
}
const artifact = (artifactId: string, version: string, extension = 'jar', group = 'org/jahia/modules') =>
  `${PUBLIC_REPOSITORY}/${group}/${artifactId}/${version}/${artifactId}-${version}.${extension}`
const pack = `${PUBLIC_REPOSITORY}/org/jahia/packages/jahia-core-modules/8.2.2.1/jahia-core-modules-8.2.2.1-provisioning.yaml`
const storeModule = (name: string, versions: Record<string, string>, groupId = 'org.jahia.modules') => ({
  groupId,
  name,
  versions: Object.entries(versions).map(([version, required]) => ({
    version,
    requiredVersion: `version-${required}`,
    downloadUrl: `${STORE_PROXY}/${name}-${version}.jar`
  }))
})
const served = {
  [pack]: [
    '- installBundle:',
    "  - url: 'mvn:org.jahia.modules/app-shell/3.3.0'",
    '    startLevel: 85',
    "  - url: 'mvn:org.jahia.modules/graphql-dxm-provider/3.4.0'",
    "  - url: 'mvn:org.jahia.modules/jcontent/3.2.0'",
    "  - url: 'mvn:org.jahia.modules/luxe/0.2.0'",
    "  - url: 'mvn:org.jahia.modules/community/1.0.0'",
    "  - url: 'mvn:org.jahia.modules/tags/8.2.0'"
  ].join('\n'),
  [`${STORE}/contents/modules-repository.moduleList.json`]: JSON.stringify([
    {
      modules: [
        storeModule('app-shell', {'4.0.0': '8.2.0.0'}),
        storeModule('graphql-dxm-provider', {'3.10.0': '8.2.0.0'}),
        storeModule('jcontent', {'3.8.1': '8.2.1.0', '4.0.0': '8.2.4.0'}),
        storeModule('luxe', {'1.1.0': '8.2.0.0'}),
        storeModule('community', {'1.2.0': '8.2.0.0', '0.9.0': '8.2.0.0'}),
        storeModule('not-shipped', {'1.0.0': '8.2.0.0'})
      ]
    }
  ]),
  [artifact('app-shell', '3.3.0')]: jarOf('Jahia-Depends: graphql-dxm-provider\nJahia-Module-Type: system\n'),
  [artifact('graphql-dxm-provider', '3.4.0')]: jarOf('Jahia-Depends: \n'),
  [artifact('jcontent', '3.2.0')]: jarOf('Jahia-Depends: app-shell,graphql-dxm-provider\n'),
  [artifact('jcontent', '3.8.1')]: jarOf('Jahia-Depends: app-shell\n'),
  [artifact('luxe', '0.2.0')]: jarOf('Jahia-Depends: jcontent\n'),
  [artifact('luxe', '1.1.0', 'tgz')]: new Uint8Array(
    gzipSync(tarOf([['package/package.json', '{"jahia":{}}']]))
  ),
  [artifact('tags', '8.2.0')]: jarOf('Bundle-SymbolicName: tags\n'),
  // A community module is on no Nexus group: the proxy of the Store serves it, without ranges.
  [`${STORE_PROXY}/org/jahia/modules/community/1.0.0/community-1.0.0.jar`]: {
    noRanges: jarOf('Jahia-Depends: tags\n')
  },
  [`${STORE_PROXY}/community-1.2.0.jar`]: {noRanges: jarOf('Jahia-Depends: tags\n')}
}

const environment = (http = fakeHttp(served)) => {
  const files: Record<string, string> = {}
  const logs: string[] = []
  return {
    files,
    logs,
    http,
    writeFile: async (path: string, content: string) => void (files[path] = content),
    now: () => new Date('2026-11-24T10:00:00.123Z'),
    log: (message: string) => void logs.push(message)
  }
}

test('writes the script of the versions the module manager offers', async () => {
  const env = environment()
  const outputs = await run(inputs, env)
  expect(outputs).toEqual({
    provisioningPath: 'out/modules.yml',
    matrixPath: 'out/matrix.json',
    modules: 6,
    upgraded: 3
  })
  expect(env.files['out/modules.yml']).toBe(
    [
      '# Jahia 8.2.2.1: the 6 modules it ships, each at the version its module manager offers from the Store.',
      `# 3 of them are newer than shipped. Store: ${STORE}`,
      '# Generated on 2026-11-24T10:00:00Z by jahia-modules-action/modules-provisioning.',
      '- installOrUpgradeBundle:',
      "    - url: 'mvn:org.jahia.modules/app-shell/3.3.0'  # mandatory: the module manager does not offer 4.0.0",
      '      startLevel: 85',
      "    - url: 'mvn:org.jahia.modules/community/1.2.0'  # shipped 1.0.0",
      "    - url: 'mvn:org.jahia.modules/graphql-dxm-provider/3.4.0'  # mandatory: the module manager does not offer 3.10.0",
      "    - url: 'mvn:org.jahia.modules/jcontent/3.8.1'  # shipped 3.2.0",
      "    - url: 'js:mvn:org.jahia.modules/luxe/1.1.0/tgz'  # shipped 0.2.0",
      "    - url: 'mvn:org.jahia.modules/tags/8.2.0'",
      '  autoStart: true',
      ''
    ].join('\n')
  )
  expect(env.logs.at(-1)).toContain('3 newer than shipped, 2 offers withheld on mandatory modules')
})

test('writes the matrix the script comes from', async () => {
  const env = environment()
  await run(inputs, env)
  const matrix = JSON.parse(env.files['out/matrix.json'] ?? '')
  expect(matrix.generatedAt).toBe('2026-11-24T10:00:00Z')
  expect(matrix.repositories).toEqual([PUBLIC_REPOSITORY, STORE_PROXY])
  const release = matrix.jahia['8.2.2.1']
  expect(release.mandatoryModules).toEqual(['app-shell', 'graphql-dxm-provider'])
  expect(release.storeOffers).toEqual({
    'org.jahia.modules:app-shell': '4.0.0',
    'org.jahia.modules:community': '1.2.0',
    'org.jahia.modules:graphql-dxm-provider': '3.10.0',
    'org.jahia.modules:jcontent': '3.8.1',
    'org.jahia.modules:luxe': '1.1.0'
  })
  expect(Object.keys(matrix.modules['org.jahia.modules:jcontent'].versions)).toEqual(['3.2.0', '3.8.1'])
  expect(matrix.modules['org.jahia.modules:luxe'].versions['1.1.0'].packaging).toBe('tgz')
  expect(Object.keys(matrix.modules['org.jahia.modules:tags'].versions)).toEqual(['8.2.0'])
  expect(Object.keys(matrix.store.modules)).toContain('org.jahia.modules:not-shipped')
})

test('writes the shipped versions without reading the Store', async () => {
  const env = environment()
  const outputs = await run({...inputs, versions: 'shipped'}, env)
  expect(outputs.upgraded).toBe(0)
  expect(env.http.calls.some(url => url.startsWith(STORE) || url.startsWith(STORE_PROXY))).toBe(false)
  expect(env.files['out/modules.yml']).toContain("    - url: 'mvn:org.jahia.modules/jcontent/3.2.0'\n")
  expect(JSON.parse(env.files['out/matrix.json'] ?? '').store).toBeUndefined()
})

test('fails for a release with no pack on Nexus', async () => {
  const env = environment()
  await expect(run({...inputs, jahiaVersion: '9.9.9.9'}, env)).rejects.toThrow(
    'Jahia 9.9.9.9 has no pack on Nexus'
  )
  expect(env.files).toEqual({})
})
