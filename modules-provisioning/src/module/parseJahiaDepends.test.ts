import {expect, test} from 'vitest'
import {parseJahiaDepends} from './parseJahiaDepends.js'

test('reads names, versions and the optional flag', () => {
  expect(parseJahiaDepends('default,graphql-dxm-provider=[3.0,4),ldap;optional,tags=1.2;optional')).toEqual([
    {module: 'default'},
    {module: 'graphql-dxm-provider', version: '[3.0,4)'},
    {module: 'ldap', optional: true},
    {module: 'tags', version: '1.2', optional: true}
  ])
})

test('is empty without the attribute', () => {
  expect(parseJahiaDepends(undefined)).toEqual([])
  expect(parseJahiaDepends('')).toEqual([])
})
