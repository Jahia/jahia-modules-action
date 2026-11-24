import {expect, test} from 'vitest'
import {moduleUrl} from './moduleUrl.js'

const module = {
  groupId: 'g',
  artifactId: 'a',
  version: '1.0',
  pack: 'p',
  shippedVersion: '1.0',
  mandatory: false
}

test('names a Java and a JavaScript module', () => {
  expect(moduleUrl(module)).toBe('mvn:g/a/1.0')
  expect(moduleUrl({...module, type: 'js'})).toBe('js:mvn:g/a/1.0/tgz')
})
