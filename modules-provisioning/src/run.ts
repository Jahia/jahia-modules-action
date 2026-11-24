import {CONCURRENCY, NON_MANAGEABLE_MODULES, STORE_PROXY} from './constants.js'
import {mandatoryModules} from './mandatory/mandatoryModules.js'
import {readModuleVersion} from './module/readModuleVersion.js'
import {provisioningModules} from './provisioning/provisioningModules.js'
import {renderProvisioning} from './provisioning/renderProvisioning.js'
import {readRelease} from './release/readRelease.js'
import {repositories as mavenRepositories} from './repositories.js'
import {readStore} from './store/readStore.js'
import {storeOffer} from './store/storeOffer.js'
import {withPackaging} from './provisioning/withPackaging.js'
import type {Environment, Inputs, ModuleVersion, Outputs} from './types.js'
import {mapLimit} from './util/mapLimit.js'
import {moduleKey} from './util/moduleKey.js'

/** Write the provisioning script of the modules of one Jahia release, and the matrix it comes from. */
export const run = async (inputs: Inputs, {http, writeFile, now, log}: Environment): Promise<Outputs> => {
  const {jahiaVersion, versions, storeUrl} = inputs
  const nexus = mavenRepositories(inputs.nexusUsername, inputs.nexusPassword)
  // The Store serves the modules Nexus lacks, the community ones, through its Maven proxy.
  const sources = versions === 'store' ? [...nexus, STORE_PROXY] : nexus
  const store = versions === 'store' ? await readStore(http, storeUrl) : {}
  if (versions === 'store') log(`store ${storeUrl}: ${Object.keys(store).length} modules`)

  const release = await readRelease(http, nexus, jahiaVersion)
  if (release.modules.length === 0) throw new Error(`Jahia ${jahiaVersion} has no pack on Nexus`)
  log(`release ${jahiaVersion}: ${release.modules.length} modules in its packs`)

  const shipped = await mapLimit(release.modules, CONCURRENCY, module =>
    readModuleVersion(http, sources, module)
  )
  const mandatory = mandatoryModules(
    Object.fromEntries(
      release.modules.map((module, index) => [
        module.artifactId,
        (shipped[index]?.jahiaDepends ?? []).map(dependency => dependency.module)
      ])
    ),
    NON_MANAGEABLE_MODULES
  )
  const offers = Object.fromEntries(
    release.modules.flatMap(module => {
      const listed = store[moduleKey(module)]
      const offer = listed && storeOffer(listed, jahiaVersion)
      return offer ? [[moduleKey(module), offer]] : []
    })
  )
  const planned = provisioningModules(release.modules, offers, mandatory, versions)

  // The packaging of an offered version names its url: a module can become a JavaScript module.
  const offered = await mapLimit(planned, CONCURRENCY, async (module): Promise<ModuleVersion | undefined> =>
    module.version === module.shippedVersion
      ? undefined
      : readModuleVersion(
          http,
          sources,
          module,
          store[moduleKey(module)]?.versions[module.version]?.downloadUrl
        )
  )
  const modules = planned.map((module, index) => withPackaging(module, offered[index]?.packaging))

  const generatedAt = now()
    .toISOString()
    .replace(/\.\d+Z$/, 'Z')
  const upgraded = modules.filter(module => module.version !== module.shippedVersion)
  await writeFile(
    inputs.provisioningPath,
    renderProvisioning(modules, {jahiaVersion, versions, storeUrl, generatedAt})
  )
  await writeFile(
    inputs.matrixPath,
    JSON.stringify(
      {
        generatedAt,
        repositories: sources,
        jahia: {
          [jahiaVersion]: {...release, storeOffers: offers, mandatoryModules: [...mandatory].toSorted()}
        },
        modules: Object.fromEntries(
          release.modules.map((module, index) => [
            moduleKey(module),
            {
              groupId: module.groupId,
              artifactId: module.artifactId,
              versions: {
                [module.version]: shipped[index],
                ...(offered[index] ? {[planned[index]?.version ?? module.version]: offered[index]} : {})
              }
            }
          ])
        ),
        ...(versions === 'store' ? {store: {url: storeUrl, modules: store}} : {})
      },
      null,
      2
    ) + '\n'
  )
  log(
    `wrote ${inputs.provisioningPath}: ${modules.length} modules of Jahia ${jahiaVersion}, ` +
      `${upgraded.length} newer than shipped, ${modules.filter(module => module.withheldVersion).length} offers withheld on mandatory modules`
  )
  return {
    provisioningPath: inputs.provisioningPath,
    matrixPath: inputs.matrixPath,
    modules: modules.length,
    upgraded: upgraded.length
  }
}
