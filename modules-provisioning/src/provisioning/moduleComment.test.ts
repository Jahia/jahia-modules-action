import {expect, test} from 'vitest'
import {moduleComment} from './moduleComment.js'

const module = {
  groupId: 'g',
  artifactId: 'a',
  version: '1.0',
  pack: 'p',
  shippedVersion: '1.0',
  mandatory: false
}

test('says where the version differs from the shipped one', () => {
  expect(moduleComment(module)).toBe('')
  expect(moduleComment({...module, version: '2.0'})).toBe('  # shipped 1.0')
  expect(moduleComment({...module, mandatory: true, withheldVersion: '2.0'})).toBe(
    '  # mandatory: the module manager does not offer 2.0'
  )
})
