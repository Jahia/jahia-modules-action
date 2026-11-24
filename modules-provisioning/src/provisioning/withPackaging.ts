import type {ModuleVersion, ProvisioningModule} from '../types.js'

/** A module of the script with the type its packaging names: a tgz is a JavaScript module. */
export const withPackaging = (
  module: ProvisioningModule,
  packaging: ModuleVersion['packaging']
): ProvisioningModule => {
  if (packaging === undefined) return module
  const java = Object.fromEntries(
    Object.entries(module).filter(([key]) => key !== 'type')
  ) as ProvisioningModule
  return packaging === 'tgz' ? {...java, type: 'js'} : java
}
