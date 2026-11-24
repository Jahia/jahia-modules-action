import {expect, test} from 'vitest'
import {storeOffer} from './storeOffer.js'

const module = {
  groupId: 'org.jahia.modules',
  artifactId: 'jcontent',
  versions: {
    '2.20.0': {requiredVersion: '8.1.3.0'},
    '3.2.0': {requiredVersion: '8.2.0.0'},
    '3.10.0': {requiredVersion: '8.2.1.0'},
    '3.8.1': {requiredVersion: '8.2.1.0'},
    '4.0.0': {requiredVersion: '8.2.4.0'},
    '1.0.0': {requiredVersion: '7.3.0.0'}
  }
}

test('offers the newest version the release can run, on its major', () => {
  expect(storeOffer(module, '8.2.2.1')).toBe('3.10.0')
  expect(storeOffer(module, '8.2.0.4')).toBe('3.2.0')
  expect(storeOffer(module, '8.1.9.6')).toBe('2.20.0')
  expect(storeOffer(module, '8.0.3.0')).toBeUndefined()
  expect(storeOffer(module, '7.3.9.0')).toBe('1.0.0')
})
