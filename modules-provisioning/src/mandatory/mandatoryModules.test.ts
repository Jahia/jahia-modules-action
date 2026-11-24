import {expect, test} from 'vitest'
import {mandatoryModules} from './mandatoryModules.js'

const dependencies = {
  'app-shell': ['graphql-dxm-provider', 'jquery'],
  'graphql-dxm-provider': ['default'],
  default: ['app-shell'],
  jquery: [],
  jcontent: ['app-shell'],
  serverSettings: ['not-shipped']
}

test('follows Jahia-Depends through every level, and stops on a cycle', () => {
  expect(
    [...mandatoryModules(dependencies, ['app-shell', 'serverSettings', 'siteSettings'])].toSorted()
  ).toEqual(['app-shell', 'default', 'graphql-dxm-provider', 'jquery', 'serverSettings'])
})

test('is empty when the release ships none of the roots', () => {
  expect(mandatoryModules(dependencies, ['siteSettings']).size).toBe(0)
})
