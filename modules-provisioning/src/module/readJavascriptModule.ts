import {gunzipSync} from 'node:zlib'
import {extractTarEntry} from '../tar/extractTarEntry.js'
import type {ModuleVersion} from '../types.js'
import {parseJahiaDepends} from './parseJahiaDepends.js'

/** A JavaScript module is an npm package: its package.json holds the Jahia metadata. */
export const readJavascriptModule = (tgz: Uint8Array): ModuleVersion => {
  const entry = extractTarEntry(
    new Uint8Array(gunzipSync(tgz)),
    name => name.replace(/^\.\//, '') === 'package/package.json'
  )
  if (entry === undefined) return {packaging: 'tgz', error: 'no package.json'}
  const jahia = (JSON.parse(new TextDecoder().decode(entry)).jahia ?? {}) as Record<
    string,
    string | undefined
  >
  return {
    packaging: 'tgz',
    moduleType: jahia['module-type'],
    jahiaRequiredVersion: jahia['required-version'],
    jahiaDepends: parseJahiaDepends(jahia['module-dependencies'])
  }
}
