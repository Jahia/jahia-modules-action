import {artifactPath} from '../http/artifactPath.js'
import {openFirstRemoteFile} from '../remote/openFirstRemoteFile.js'
import type {Coordinate, Http, ModuleVersion} from '../types.js'
import {readJavaModule} from './readJavaModule.js'
import {readJavascriptModule} from './readJavascriptModule.js'

/**
 * One version of a module, read from the first repository that has its jar or its tgz, then from the
 * URL the Store names. A module that cannot be read is an entry with an error, never a failed run.
 */
export const readModuleVersion = async (
  http: Http,
  repositories: string[],
  {groupId, artifactId, version}: Coordinate,
  storeUrl?: string
): Promise<ModuleVersion> => {
  try {
    const urls = ['jar', 'tgz'].flatMap(extension =>
      repositories.map(
        repository =>
          `${repository}/${artifactPath(groupId, artifactId, version, `${artifactId}-${version}.${extension}`)}`
      )
    )
    const file = await openFirstRemoteFile(http, [...urls, ...(storeUrl ? [storeUrl] : [])])
    if (file === undefined) return {error: 'no jar'}
    const magic = await file.read(0, 2)
    return magic[0] === 0x1f && magic[1] === 0x8b
      ? readJavascriptModule(await file.read(0, file.size))
      : await readJavaModule(file)
  } catch (error) {
    return {error: error instanceof Error ? error.message : String(error)}
  }
}
