import type {StoreModule} from '../types.js'
import {compareVersions} from '../version/compareVersions.js'
import {versionTokens} from '../version/versionTokens.js'

/**
 * The version the module manager of a Jahia release reads for a module of the Store: the newest
 * one whose required version is at most the release, on the same major (ForgeService).
 */
export const storeOffer = (module: StoreModule, jahiaVersion: string): string | undefined =>
  Object.entries(module.versions)
    .filter(
      ([, {requiredVersion}]) =>
        compareVersions(requiredVersion, jahiaVersion) <= 0 &&
        versionTokens(requiredVersion)[0] === versionTokens(jahiaVersion)[0]
    )
    .map(([version]) => version)
    .toSorted(compareVersions)
    .at(-1)
