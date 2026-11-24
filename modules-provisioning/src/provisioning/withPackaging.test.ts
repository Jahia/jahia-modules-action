import {expect, test} from 'vitest'
import {withPackaging} from './withPackaging.js'

const module = {
  groupId: 'g',
  artifactId: 'a',
  version: '1.0',
  pack: 'p',
  shippedVersion: '1.0',
  mandatory: false
}

test('follows the packaging of the version, and keeps the module when it is unknown', () => {
  expect(withPackaging(module, 'tgz').type).toBe('js')
  expect('type' in withPackaging({...module, type: 'js'}, 'jar')).toBe(false)
  expect(withPackaging({...module, type: 'js'}, undefined).type).toBe('js')
  expect(withPackaging(module, 'jar')).toEqual(module)
})
