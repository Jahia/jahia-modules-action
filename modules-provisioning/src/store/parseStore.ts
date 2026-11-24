import type {Store, StoreVersion} from '../types.js'

type RawVersion = {version: string; requiredVersion: string; downloadUrl?: string}
type RawModule = {groupId: string; name: string; title?: string; status?: string; versions?: RawVersion[]}

/** The module list that Jahia's module manager reads from a store, keyed by groupId:artifactId. */
export const parseStore = (json: string): Store => {
  const [repository] = JSON.parse(json) as {modules: RawModule[]}[]
  return Object.fromEntries(
    (repository?.modules ?? []).map(module => [
      `${module.groupId}:${module.name}`,
      {
        groupId: module.groupId,
        artifactId: module.name,
        title: module.title,
        status: module.status,
        versions: Object.fromEntries(
          (module.versions ?? []).map((version): [string, StoreVersion] => [
            version.version,
            {
              requiredVersion: version.requiredVersion.replace('version-', ''),
              downloadUrl: version.downloadUrl
            }
          ])
        )
      }
    ])
  )
}
