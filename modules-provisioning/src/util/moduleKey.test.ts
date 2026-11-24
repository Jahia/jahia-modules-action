import {expect, test} from 'vitest'
import {moduleKey} from './moduleKey.js'

test('joins the group and the artifact', () => {
  expect(moduleKey({groupId: 'org.jahia.modules', artifactId: 'tags'})).toBe('org.jahia.modules:tags')
})
