import {readFileSync} from 'node:fs'
import {describe, expect, test} from 'vitest'
import {NON_MANAGEABLE_MODULES} from './constants.js'
import {mandatoryModules} from './mandatory/mandatoryModules.js'
import {provisioningModules} from './provisioning/provisioningModules.js'
import {storeOffer} from './store/storeOffer.js'
import type {ReleaseModule, Store} from './types.js'
import {compareVersions} from './version/compareVersions.js'

type Page = {
  jahiaVersion: string
  modules: ReleaseModule[]
  depends: Record<string, string[]>
  store: Store
  page: {installed: Record<string, string>; updates: Record<string, string>; mandatory: string[]}
}

/**
 * Each file is one "Installed modules" page of a standalone Jahia, read row by row on every page of
 * its list on 2026-11-24, with the packs, the Jahia-Depends and the Store of that day. The script
 * must name, for each module the page lists, the version the page offers.
 */
describe.each(['8.1.9.6', '8.2.1.0', '8.2.2.1', '8.2.3.7'])(
  'the module manager page of Jahia %s',
  version => {
    const {jahiaVersion, modules, depends, store, page} = JSON.parse(
      readFileSync(new URL(`./testing/pages/${version}.json`, import.meta.url), 'utf8')
    ) as Page
    const mandatory = mandatoryModules(depends, NON_MANAGEABLE_MODULES)
    const offers = Object.fromEntries(
      Object.entries(store).flatMap(([key, module]) => {
        const offer = storeOffer(module, jahiaVersion)
        return offer ? [[key, offer]] : []
      })
    )
    const script = provisioningModules(modules, offers, mandatory, 'store')
    const listed = script.filter(module => module.artifactId in page.installed)

    test('lists the modules the page lists', () => {
      expect(listed.length).toBe(Object.keys(page.installed).length)
    })

    test('marks the same modules as mandatory', () => {
      expect(
        listed
          .filter(module => module.mandatory)
          .map(module => module.artifactId)
          .toSorted()
      ).toEqual(page.mandatory.toSorted())
    })

    test('offers the same updates, at the same versions', () => {
      const updates = Object.fromEntries(
        listed
          .filter(module => module.version !== module.shippedVersion)
          .map(module => [module.artifactId, module.version])
      )
      expect(updates).toEqual(page.updates)
    })

    test('names the installed version of every other module', () => {
      listed
        .filter(module => !(module.artifactId in page.updates))
        .forEach(module => expect(module.version, module.artifactId).toBe(page.installed[module.artifactId]))
    })

    test('never goes back to an older version than shipped', () => {
      script.forEach(module =>
        expect(
          compareVersions(module.version, module.shippedVersion),
          module.artifactId
        ).toBeGreaterThanOrEqual(0)
      )
    })
  }
)
