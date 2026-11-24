import {gzipSync} from 'node:zlib'
import {expect, test} from 'vitest'
import {tarOf} from '../testing/tarOf.js'
import {readJavascriptModule} from './readJavascriptModule.js'

const tgzOf = (files: [string, string][]) => new Uint8Array(gzipSync(tarOf(files)))

test('reads the jahia block of package.json', () => {
  const tgz = tgzOf([
    ['./package/README.md', 'read me'],
    [
      './package/package.json',
      JSON.stringify({
        name: 'luxe',
        jahia: {
          'module-type': 'templatesSet',
          'required-version': '8.2.1.0',
          'module-dependencies': 'default,jcontent'
        }
      })
    ]
  ])
  expect(readJavascriptModule(tgz)).toEqual({
    packaging: 'tgz',
    moduleType: 'templatesSet',
    jahiaRequiredVersion: '8.2.1.0',
    jahiaDepends: [{module: 'default'}, {module: 'jcontent'}]
  })
})

test('accepts a package with no jahia block, and reports one with no package.json', () => {
  expect(readJavascriptModule(tgzOf([['package/package.json', '{}']]))).toEqual({
    packaging: 'tgz',
    moduleType: undefined,
    jahiaRequiredVersion: undefined,
    jahiaDepends: []
  })
  expect(readJavascriptModule(tgzOf([['package/index.js', '']]))).toEqual({
    packaging: 'tgz',
    error: 'no package.json'
  })
})
