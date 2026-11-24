import type {ProvisioningModule} from '../types.js'

/** What the line of a module says beside its url: where its version differs from the shipped one. */
export const moduleComment = ({version, shippedVersion, withheldVersion}: ProvisioningModule): string => {
  if (version !== shippedVersion) return `  # shipped ${shippedVersion}`
  if (withheldVersion) return `  # mandatory: the module manager does not offer ${withheldVersion}`
  return ''
}
