import {expect, test} from 'vitest'
import {artifactPath} from './artifactPath.js'

test('builds the Maven path at each depth', () => {
  expect(artifactPath('org.jahia.modules', 'jcontent')).toBe('org/jahia/modules/jcontent')
  expect(artifactPath('org.jahia.modules', 'jcontent', '3.8.1')).toBe('org/jahia/modules/jcontent/3.8.1')
  expect(artifactPath('org.jahia.modules', 'jcontent', '3.8.1', 'jcontent-3.8.1.jar')).toBe(
    'org/jahia/modules/jcontent/3.8.1/jcontent-3.8.1.jar'
  )
})
