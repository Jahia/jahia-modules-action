import {zipSync} from 'fflate'
import {expect, test} from 'vitest'
import {jarOf} from '../testing/jarOf.js'
import {remoteFileOf} from '../testing/remoteFileOf.js'
import {readJavaModule} from './readJavaModule.js'

test('reads what the manifest states', async () => {
  const jar = jarOf(
    'Bundle-SymbolicName: jcontent\nJahia-Depends: default,app-shell=[3,4)\nJahia-Module-Type: system\nJahia-Required-Version: 8.2.0.0\nOther: x\n'
  )
  expect(await readJavaModule(remoteFileOf(jar))).toEqual({
    packaging: 'jar',
    moduleType: 'system',
    jahiaRequiredVersion: '8.2.0.0',
    jahiaDepends: [{module: 'default'}, {module: 'app-shell', version: '[3,4)'}],
    manifest: {
      'Bundle-SymbolicName': 'jcontent',
      'Jahia-Required-Version': '8.2.0.0',
      'Jahia-Depends': 'default,app-shell=[3,4)',
      'Jahia-Module-Type': 'system'
    }
  })
})

test('reports a jar without a manifest', async () => {
  const jar = zipSync({'a.txt': new Uint8Array(1)})
  expect(await readJavaModule(remoteFileOf(jar))).toEqual({packaging: 'jar', error: 'no manifest'})
})
