import {PACKS, PACKS_GROUP} from '../constants.js'
import {artifactPath} from '../http/artifactPath.js'
import {fetchText} from '../http/fetchText.js'
import type {Http, Release} from '../types.js'
import {parsePackProvisioning} from './parsePackProvisioning.js'

/** The modules a Jahia release ships, from the provisioning YAML of each of its packs. */
export const readRelease = async (http: Http, repositories: string[], version: string): Promise<Release> => {
  const packs = await Promise.all(
    PACKS.map(async pack => {
      const text = await fetchText(
        http,
        repositories,
        artifactPath(PACKS_GROUP, pack, version, `${pack}-${version}-provisioning.yaml`)
      )
      return {pack, modules: text === undefined ? undefined : parsePackProvisioning(text, pack)}
    })
  )
  return {
    packs: Object.fromEntries(packs.map(({pack, modules}) => [pack, modules?.length ?? null])),
    modules: packs
      .flatMap(({modules}) => modules ?? [])
      .toSorted((a, b) => a.artifactId.localeCompare(b.artifactId) || a.groupId.localeCompare(b.groupId))
  }
}
