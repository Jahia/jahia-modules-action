import {gzipSync} from 'node:zlib'
import {expect, test} from 'vitest'
import {fakeHttp} from '../testing/fakeHttp.js'
import {jarOf} from '../testing/jarOf.js'
import {tarOf} from '../testing/tarOf.js'
import {readModuleVersion} from './readModuleVersion.js'

const module = {groupId: 'org.jahia.modules', artifactId: 'tags', version: '8.2.0'}
const path = 'org/jahia/modules/tags/8.2.0/tags-8.2.0'
const jar = jarOf('Jahia-Depends: default\n')
const tgz = new Uint8Array(gzipSync(tarOf([['package/package.json', '{"jahia":{"module-type":"module"}}']])))

test('reads the jar of the first repository that has it', async () => {
  const http = fakeHttp({[`https://b/${path}.jar`]: jar})
  const version = await readModuleVersion(http, ['https://a', 'https://b'], module)
  expect(version).toMatchObject({packaging: 'jar', jahiaDepends: [{module: 'default'}]})
})

test('reads a JavaScript module from its tgz', async () => {
  const http = fakeHttp({[`https://a/${path}.tgz`]: tgz})
  expect(await readModuleVersion(http, ['https://a'], module)).toMatchObject({
    packaging: 'tgz',
    moduleType: 'module'
  })
})

test('falls back on the URL the Store names', async () => {
  const http = fakeHttp({'https://store/download/tags.jar': {noRanges: jar}})
  expect(
    await readModuleVersion(http, ['https://a'], module, 'https://store/download/tags.jar')
  ).toMatchObject({
    packaging: 'jar'
  })
})

test('reports a module no repository has, and one that cannot be read', async () => {
  expect(await readModuleVersion(fakeHttp({}), ['https://a'], module)).toEqual({error: 'no jar'})
  const broken = fakeHttp({[`https://a/${path}.jar`]: new Uint8Array(40)})
  expect(await readModuleVersion(broken, ['https://a'], module)).toEqual({
    error: 'not a zip: no end of central directory'
  })
  const failing = async () => Promise.reject('offline')
  expect(await readModuleVersion(failing, ['https://a'], module)).toEqual({error: 'offline'})
})
