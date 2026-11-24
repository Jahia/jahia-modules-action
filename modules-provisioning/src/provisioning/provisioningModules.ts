import type {ProvisioningModule, ReleaseModule, VersionsMode} from '../types.js'
import {compareVersions} from '../version/compareVersions.js'

/**
 * Each module a release ships, at the version of the script. In store mode that is the version the
 * page of the module manager offers: the offer of the Store, when it is newer than the shipped
 * version and the module is not a mandatory one. An offer the page withholds is kept beside it.
 */
export const provisioningModules = (
  shipped: ReleaseModule[],
  offers: Record<string, string>,
  mandatory: ReadonlySet<string>,
  versions: VersionsMode
): ProvisioningModule[] =>
  shipped.map(module => {
    const offer = versions === 'store' ? offers[`${module.groupId}:${module.artifactId}`] : undefined
    const newer = offer !== undefined && compareVersions(offer, module.version) > 0
    const isMandatory = mandatory.has(module.artifactId)
    return {
      ...module,
      version: newer && !isMandatory ? offer : module.version,
      shippedVersion: module.version,
      mandatory: isMandatory,
      ...(newer && isMandatory ? {withheldVersion: offer} : {})
    }
  })
