import {MANIFEST_KEYS} from '../constants.js'
import type {ModuleVersion, RemoteFile} from '../types.js'
import {readZipEntry} from '../zip/readZipEntry.js'
import {parseJahiaDepends} from './parseJahiaDepends.js'
import {parseManifest} from './parseManifest.js'

/** What the manifest of a module jar states about it. */
export const readJavaModule = async (file: RemoteFile): Promise<ModuleVersion> => {
  const bytes = await readZipEntry(file, 'META-INF/MANIFEST.MF')
  if (bytes === undefined) return {packaging: 'jar', error: 'no manifest'}
  const manifest = parseManifest(new TextDecoder().decode(bytes))
  return {
    packaging: 'jar',
    moduleType: manifest['Jahia-Module-Type'],
    jahiaRequiredVersion: manifest['Jahia-Required-Version'],
    jahiaDepends: parseJahiaDepends(manifest['Jahia-Depends']),
    manifest: Object.fromEntries(
      MANIFEST_KEYS.filter(key => key in manifest).map(key => [key, manifest[key] ?? ''])
    )
  }
}
